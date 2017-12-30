# Asyncronous HTTP server

## General principles
This repository contains a script with an multithread asyncronous web server based on asyncio library. 
The requirements and general principles of this server was described [here](https://github.com/s-stupnikov/http-test-suite)

##AB testing results

### General information

| **Name**             | **Value**                                         |
|----------------------|---------------------------------------------------|
| Server Software      | Asynchronous                                      |
| Server Hostname      | 127.0.0.1                                         |
| Server Port          | 80                                                |
| Document Path        | /                                                 |
| Document Length      | 0 bytes                                           |
| Concurrency Level    | 100                                               |
| Time taken for tests | 49.555 seconds                                    |
| Complete requests    | 50000                                             |
| Failed requests      | 0                                                 |
| Non-2xx responses    | 50000                                             |
| Total transferred    | 5400000 bytes                                     |
| HTML transferred     | 0 bytes                                           |
| Requests per second  | 1008.99 [#/sec] (mean)                            |
| Time per request     | 99.109 [ms] (mean)                                |
| Time per request     | 0.991 [ms] (mean, across all concurrent requests) |
| Transfer rate        | 106.42 [Kbytes/sec] received                      |


### Connection Times (ms)
| Indicator  | min | mean | [+/-sd] | median | max |
|------------|-----|------|---------|--------|-----|
| Connect    | 0   | 1    | 0.5     | 1      | 5   |
| Processing | 40  | 98   | 8.9     | 96     | 168 |
| Waiting    | 36  | 78   | 15.3    | 80     | 166 |
| Total      | 41  | 99   | 9       | 97     | 169 |


### Percentage of the requests served within a certain time (ms)
|      |                       |
|------|-----------------------|
| 50%  | 97                    |
| 66%  | 98                    |
| 75%  | 99                    |
| 80%  | 100                   |
| 90%  | 102                   |
| 95%  | 105                   |
| 98%  | 137                   |
| 99%  | 149                   |
| 100% | 169 (longest request) |