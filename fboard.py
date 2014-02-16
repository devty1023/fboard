"""
    fboard
    ~~~
    
    enhancing fb group. 
    sort posts by 'hotness', 'most liked', 'most commented', etc.
    sort users by score (point per likes on posts he/she authored)

    heavily influneced by Armin Ronacher's flask apps
    
    :copyright: (c) Copyright 2014 by devty
    :license: BSD, see LICENSE for detail
"""
from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy

import requests
import json
import time, calendar

app = Flask(__name__)
app.config.from_object('_config')
db = SQLAlchemy(app)

"""
DB
"""
class Post(db.Model):
    """ 
    represnts a single post
    """
    id = db.Column('post_id', db.Integer, 
                    primary_key=True)
    summary = db.Column(db.String(100))
    content = db.Column(db.String)
    count_likes = db.Column(db.Integer)
    count_comments = db.Column(db.Integer)
    score = db.Column(db.Integer)
    hot = db.Column(db.Integer)

    def __init__(self, id, summary, content, count_likes, 
                 count_comments, score, hot):
        self.id = id
        self.summary = summary
        self.content = content
        self.count_likes = count_likes
        self.count_comments = count_comments
        self.score = score
        self.hot = hot


"""
FB
"""
class FBGroupFeed(object):
    def __init__(self, group_id, app_id, app_secret):
        self.group_id = group_id
        self.app_id = app_id
        self.app_secret = app_secret
        self.more_link = ''

        self.access_token = app_id + '|' + app_secret
        self.path = 'https://graph.facebook.com/' + \
                     group_id + '/feed'
                    
        self.path_graph = 'https://graph.facebook.com/'

        self.fb_time_format = '%Y-%m-%dT%H:%M:%S+0000'


    def get_feed(self, limit=500):
        payload = { 'access_token': self.access_token, 
                    'fields': """likes.summary(true),
                                message,comments,from,
                                type,picture,link,
                                created_time,actions""",
                    'limit': limit
                  }

        try:
            res = requests.request('GET', self.path, params=payload)
        except requests.HTTPError as e:
            raise Exception() 

        res_json = json.loads(res.content)
        if res_json['data']:
            # save next link
            self.more_link = res_json['paging']['next']
            return res_json['data']
        else:
            return dict()

    def get_more_feed(self):
        if self.more_link:
            try:
                res = requests.request('GET', self.more_link)
            except requests.HTTPError as e:
                raise Exception()

            res_json = json.loads(res.content)
            if res_json['data']:
                # save next link
                self.more_link = res_json['paging']['next']
                return res_json['data']
            else:
                self.more_link = ''
                return dict()

        return dict()

    def get_recent_feed(self, ref_time, limit=500):
        feed = self.get_feed(limit=limit)
        recent_feed = []

        for post in feed:
            # post time since eposh
            post_time = calendar.timegm(time.strptime(post['updated_time'], self.fb_time_format))
            if post_time > ref_time:
                recent_feed.append(post)

        return recent_feed

    def get_comments(self, post_id, limit=5000):
        payload = { 'access_token': self.access_token, 
                    'fields': "comments,actions",
                    'limit': limit
                  }

        try:
            res = requests.request('GET', self.path_graph + post_id, params=payload)
        except requests.HTTPError as e:
            raise Exception() 

        if 'comments' in json.loads(res.content):
            return json.loads(res.content)['comments']['data'] 
        else:
            return dict()


