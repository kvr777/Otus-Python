# Asyncronous web crawler

### General principles
This repository contains a script that check top news from Y combinator site (through [Hacker News API](https://github.com/HackerNews/API) ) and saves the web pages of these news and urls from comments to local folder. You can select how much sites to select, period between the cycles and other parameters. We use asyncio and asynchttp technology for this crawler.

### Prerequisites

Python version 3.6 and above

### Installing

No special installation procedure is required. You have to copy the script and define the parameters (path to folder etc)

### Acknowledgments

Special thanks to Yeray Diaz and his perfect [article](https://medium.com/python-pandemonium/asyncio-coroutine-patterns-beyond-await-a6121486656f) and [code](https://github.com/yeraydiazdiaz/asyncio-coroutine-patterns) that was used as a base for this script

