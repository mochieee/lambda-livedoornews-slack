#!/usr/bin/env python
# encoding: utf-8

import json
from datetime import datetime, timedelta
import requests
import lxml.html # pip install lxml
import readability # pip install readability-lxml
import os
import logging
import time


logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    # モバイルページ表示用のUser-Agent
    headers = {'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 10_3 like Mac OS X) AppleWebKit/602.1.50 (KHTML, like Gecko) CriOS/56.0.2924.75 Mobile/14E5239e Safari/602.1'}

    # 複数のページをクロールするのでSessionを使う。
    session = requests.Session()
    response_main = session.get('http://news.livedoor.com/topics/category/main/')
    root = lxml.html.fromstring(response_main.content)
    root.make_links_absolute(response_main.url)
    urls = [a.get('href') for a in root.cssselect('.hasImg a')[:10]]
    posts = []
    for url in urls:
        time.sleep(1)
        summary_response = session.get(url)
        summary_html = lxml.html.fromstring(summary_response.content)
        detail_url = summary_html.cssselect('.articleMore > a')[0].get('href')
        detail_response = session.get(detail_url, headers=headers)
        detail_html = readability.Document(detail_response.text).summary()
        detail_text = lxml.html.fromstring(detail_html).text_content().strip()
        item = {
            'title': summary_html.cssselect('.topicsTtl')[0].text_content(),
            'detail_url': detail_url,
            'summary_url': summary_response.url,
            'text': detail_text.replace('\u3000', '\n\n')
        }
        posts.append(item)
    if len(posts) > 0:
        for post in posts:
            try:
                text = f"{post['text']}\n\n<{post['summary_url']}|答え>"
                slack_message = {
                    'channel': os.environ['SLACK_CHANNEL'],
                    "attachments": [{"title": post['title'], "text": text}],
                    'username': 'livedoor news',
                }
                requests.post(os.environ['SLACK_WEBHOOK_URL'],
                              data=json.dumps(slack_message))
            except requests.exceptions.RequestException as e:
                logger.error("Request failed: %s", e)
