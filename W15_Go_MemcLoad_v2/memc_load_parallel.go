package main

import (
	"appsinstalled"
	"bufio"
	"compress/gzip"
	"errors"
	"flag"
	"fmt"
	"github.com/bradfitz/gomemcache/memcache"
	"github.com/golang/protobuf/proto"
	"github.com/stretchr/testify/assert"
	"log"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
)

const (
	NORMAL_ERR_RATE = 0.01
	numDigesters    = 20
)

type AppsInstalled struct {
	dev_type string
	dev_id   string
	lat      float64
	lon      float64
	apps     []uint32
}

//type result struct {
//	processed  int16
//	errors  int16
//}

func assertEqual(a interface{}, b interface{}) {
	if assert.ObjectsAreEqual(a, b) == false {
		log.Println("ERROR", a, " != ", b, " \r\n")
		return
	}
	log.Println("INFO Test for equality successfuly passed", " \r\n")
	return

}

func dot_rename(path string) error {
	head, old_fn := filepath.Split(path)
	// atomic in most cases
	err := os.Rename(path, filepath.Join(head, "."+old_fn))
	return err
}

func insert_appsinstalled(mc *memcache.Client, appsinstld *AppsInstalled, dry_run bool) bool {
	ua := &appsinstalled.UserApps{}
	ua.Lat = proto.Float64(appsinstld.lat)
	ua.Lon = proto.Float64(appsinstld.lon)
	ua.Apps = appsinstld.apps
	key := fmt.Sprintf("%s:%s", appsinstld.dev_type, appsinstld.dev_id)
	packed, _ := proto.Marshal(ua)
	if dry_run {
		log.Println("DEBUG %s- %s-> %s", "memc_addr", key,
			strings.Replace(ua.String(), "\n", " ", -1))
	} else {
		err := mc.Set(&memcache.Item{Key: key, Value: packed})
		if err != nil {
			log.Printf("Cannot write to memc %v: %v", "server", err)
			return false
		}
	}
	return true
}

func parse_appsinstalled(line string) (*AppsInstalled, error) {
	line_parts := strings.Split(strings.TrimSpace(line), "\t")
	if len(line_parts) != 5 {
		return nil, errors.New("Quantity of args is not valid")
	}
	dev_type, dev_id := line_parts[0], line_parts[1]
	if dev_type == "" || dev_id == "" {
		return nil, errors.New("Dev type or dev_id is not defined")
	}
	lat, lon, raw_apps := line_parts[2], line_parts[3], line_parts[4]
	var lon_num, lat_num float64
	i, err := strconv.ParseFloat(lat, 64)
	if err != nil {
		return nil, err
	} else {
		lat_num = i
	}

	i, err = strconv.ParseFloat(lon, 64)
	if err != nil {
		return nil, err
	} else {
		lon_num = i
	}

	var apps []uint32
	for _, app_item := range strings.Split(raw_apps, ",") {
		if app_item_int, err := strconv.Atoi(app_item); err == nil {
			apps = append(apps, uint32(app_item_int))
		} else {
			log.Println("INFO Not all user apps are digits: %s", line)
		}
	}

	res := &AppsInstalled{
		dev_type: dev_type,
		dev_id:   dev_id,
		lat:      lat_num,
		lon:      lon_num,
		apps:     apps,
	}

	return res, nil
}

func process_one_file(fn string, device_memc map[string]interface{},
	memc_servers map[string]*memcache.Client, dry bool) error {
	processed := 0
	ln_errors := 0
	fn, _ = filepath.Abs(filepath.Join("./", fn))
	log.Println("INFO Processing: ", fn)

	fi, err := os.Open(fn)

	if err != nil {
		log.Fatalf("ERROR Cannot read the file. Stoping the work", " \r\n")
		return err
	}
	defer fi.Close()

	fz, err := gzip.NewReader(fi)
	if err != nil {
		log.Fatalf("ERROR Cannot read the file. Stoping the work", " \r\n")
		return err
	}
	defer fz.Close()

	cr := bufio.NewScanner(fz)
	for cr.Scan() {
		line := strings.TrimSpace(cr.Text())
		if len(line) == 0 {
			continue
		}

		appsinstld, err := parse_appsinstalled(line)

		if err != nil {
			ln_errors += ln_errors
			continue
		}

		memc_addr := device_memc[appsinstld.dev_type]

		if memc_addr == 0 {
			ln_errors += ln_errors
			log.Println("ERROR Unknow device type: ", appsinstld.dev_type)
			continue
		}

		ok := insert_appsinstalled(memc_servers[appsinstld.dev_type], appsinstld, dry)

		if ok {
			processed += 1
		} else {
			ln_errors += 1
		}
	}
	//fmt.Println(processed)
	err_rate := float64(ln_errors) / float64(processed)

	if err_rate < NORMAL_ERR_RATE {
		log.Printf("INFO Acceptable error rate (%v). Successfull load ", err_rate)
	} else {
		log.Printf("ERROR High error rate (%v > %v). Failed load ", err_rate, NORMAL_ERR_RATE)
	}
	return nil
}

func process_file_and_rename(fn string, device_memc map[string]interface{},
	memc_servers map[string]*memcache.Client, dry bool) error {
	process_one_file(fn, device_memc, memc_servers, dry)
	err := dot_rename(fn)
	return err
}

func digester(done <-chan struct{}, paths <-chan string, c chan<- error,
	device_memc map[string]interface{}, memc_servers map[string]*memcache.Client, dry bool) {
	for fn := range paths {
		res := process_file_and_rename(fn, device_memc, memc_servers, dry)
		select {
		case c <- res:
		case <-done:
			return
		}
	}
}

func main_func(opts map[string]interface{}) error {

	device_memc := map[string]interface{}{
		"idfa": opts["idfa"],
		"gaid": opts["gaid"],
		"adid": opts["adid"],
		"dvid": opts["dvid"],
	}

	memc_servers := make(map[string]*memcache.Client)

	for k, v := range device_memc {
		mc := memcache.New(v.(string))
		memc_servers[k] = mc

	}

	paths_list, err := filepath.Glob(opts["pattern"].(string))
	done := make(chan struct{})
	paths := make(chan string)
	defer close(done)

	if err != nil {
		return err
	}

	if len(paths_list) == 0 {
		return errors.New("Files to process weren't found")
	}

	c := make(chan error)

	var wg sync.WaitGroup
	wg.Add(numDigesters)

	for i := 0; i < numDigesters; i++ {
		go func() {
			digester(done, paths, c, device_memc, memc_servers, opts["dry"].(bool))
			wg.Done()
		}()
	}
	go func() {
		wg.Wait()
		close(c)
	}()

	for _, path := range paths_list {
		paths <- path
	}
	close(paths)

	// End of pipeline.
	for r := range c {
		if r != nil {
			return r
		}
	}
	return nil
}

func main() {

	test := flag.Bool("t", false, "dry")
	log_file := flag.String("l", "", "log")
	dry := flag.Bool("dry", false, "dry")
	pattern := flag.String("pattern", "./data/*.tsv.gz", "Directory to search the files")
	idfa := flag.String("idfa", "127.0.0.1:33013", "Address to insert idfa")
	gaid := flag.String("gaid", "127.0.0.1:33014", "Address to insert gaid")
	adid := flag.String("adid", "127.0.0.1:33015", "Address to insert adid")
	dvid := flag.String("dvid", "127.0.0.1:33016", "Address to insert dvid")

	flag.Parse()

	opts := map[string]interface{}{
		"test":     *test,
		"log_file": *log_file,
		"dry":      *dry,
		"pattern":  *pattern,
		"idfa":     *idfa,
		"gaid":     *gaid,
		"adid":     *adid,
		"dvid":     *dvid,
	}

	if opts["log_file"] != "" {
		f, err := os.OpenFile("opts.log", os.O_WRONLY|os.O_CREATE|os.O_APPEND, 0644)
		if err != nil {
			log.Fatal(err)
		}

		defer f.Close()
		log.SetOutput(f)
	}

	log.Println("INFO: Memc loader started with options:", opts, " \n")

	err := main_func(opts)
	if err != nil {
		log.Fatalf("Unexpected error:", err)
		return
	}

}
