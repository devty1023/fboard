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
from flask import Flask, render_template
from flask.ext.sqlalchemy import SQLAlchemy
import requests
import json
import time, calendar
import math

import redis


from celery import Celery

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
    id = db.Column(db.String, primary_key=True)
    created = db.Column(db.String)
    summary = db.Column(db.String)
    count_likes = db.Column(db.Integer)
    count_comments = db.Column(db.Integer)
    link = db.Column(db.String)
    score = db.Column(db.Float)
    hot = db.Column(db.Float)
    author = db.Column(db.String)
    author_id = db.Column(db.String)
    ext_link = db.Column(db.String)


    def __init__(self, id, summary, count_likes, 
                 count_comments, score, hot, link,
                 author, author_id, created, ext_link):
        self.id = id
        self.summary = summary
        self.count_likes = count_likes
        self.count_comments = count_comments
        self.link = link
        self.score = score
        self.hot = hot
        self.author = author
        self.author_id = author_id
        self.created = created
        self.ext_link = ext_link

    def __repr__(self):
        return '<POST> id: ' + str(self.id) + ' score: ' + str(self.score) 

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
                                message,comments.summary(true),
                                from,type,picture,link,
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

    def get_recent_feed(self, ref_time, limit=5000):
        print 'get_recent_feed(' + str(ref_time) + ')'
        feed = self.get_feed(limit=limit)
        recent_feed = []

        print len(feed), " posts loaded"
        for post in feed:
            # post time since eposh
            post_time = calendar.timegm(time.strptime(post['updated_time'], 
                                                      self.fb_time_format)
                                       )

            if post_time > ref_time:
                recent_feed.append(post)

        print "got: ",len(recent_feed)
        return recent_feed

    # dont use
    def get_profile_link(self, author_id):
        r =requests.request('GET', self.path_graph + \
                                   str(author_id) + \
                                   '/picture')

        return r.url


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


"""
Celery Tasks
"""
def make_celery(app):
    celery = Celery(app.import_name, broker=app.config['CELERY_BROKER_URL'])
    celery.conf.update(app.config)
    TaskBase = celery.Task
    class ContextTask(TaskBase):
        abstract = True
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)
    celery.Task = ContextTask
    return celery

celery = make_celery(app)

@celery.task()
def update_score(post):
    # calculate hotscore
    post['score'], post['hot'] = hotness(post['count_likes'], 
                                         post['count_comments'], 
                                         post['created'])

    #print 'updating score: ' + str(post)
    # create / update database entry
    return update_or_create_post(post_id=post['post_id'],
                                 summary=post['summary'], 
                                 count_likes=post['count_likes'],
                                 count_comments=post['count_comments'],
                                 link=post['link'], 
                                 score=post['score'],
                                 hot=post['hot'],
                                 author=post['author'],
                                 author_id=post['author_id'],
                                 created=post['created'],
                                 ext_link=post['ext_link'])

      
def sync_init():
    """Synchronize with database-INIT"""
    fb = FBGroupFeed(group_id = app.config['GROUP_ID'],
                     app_id = app.config['APP_ID'],
                     app_secret = app.config['APP_SECRET'])

    ref_time = int(app.config['SYNC_START'])
    posts = fb.get_feed()
    for post in posts:
        clean_post = dict()
        clean_post['post_id'] = post['id']
        clean_post['summary'] = post.get('message', "")

        temp_likes = post.get('likes', 0)
        if not temp_likes:
            clean_post['count_likes'] = 0 
        else:
            clean_post['count_likes'] = int(post['likes']['summary']['total_count'])

        temp_comments = post.get('comments', 0)
        if not temp_comments:
            clean_post['count_comments'] = 0
        else:
            clean_post['count_comments'] = int(post['comments']['summary']['total_count'])

        clean_post['link'] = post['actions'][0]['link']
        clean_post['author'] = post['from']['name']
        clean_post['author_id'] = post['from']['id']
        clean_post['created'] = calendar.timegm(time.strptime(post['created_time'], 
                                                fb.fb_time_format)
                                               )
        print clean_post['created'], '!!!!!!!!!!!!'
 
        clean_post['ext_link'] = post.get('link', '')
        clean_post['ref_time'] = ref_time

        update_score.delay(clean_post)

    posts = fb.get_more_feed()
    while posts:
        print 'processing...', len(posts)
        for post in posts:
            clean_post = dict()
            clean_post['post_id'] = post['id']
            clean_post['summary'] = post.get('message', "")

            temp_likes = post.get('likes', 0)
            if not temp_likes:
                clean_post['count_likes'] = 0 
            else:
                clean_post['count_likes'] = int(post['likes']['summary']['total_count'])

            temp_comments = post.get('comments', 0)
            if not temp_comments:
                clean_post['count_comments'] = 0
            else:
                clean_post['count_comments'] = int(post['comments']['summary']['total_count'])

            clean_post['link'] = post['actions'][0]['link']
            clean_post['author'] = post['from']['name']
            clean_post['author_id'] = post['from']['id']
            clean_post['created'] = post['created_time']
            clean_post['created'] = calendar.timegm(time.strptime(post['created_time'], 
                                                    fb.fb_time_format)
                                                   )
            print clean_post['created'], '!!!!!!!!!!!!'
 

            clean_post['ext_link'] = post.get('link', '')
            clean_post['ref_time'] = ref_time

            update_score.delay(clean_post)
        posts = fb.get_more_feed()




@celery.task()
def sync():
    """Synchronize with database"""
    fb = FBGroupFeed(group_id = app.config['GROUP_ID'],
                     app_id = app.config['APP_ID'],
                     app_secret = app.config['APP_SECRET'])

    #GET REF_TIME FROM CACHE
    r = redis.StrictRedis(host='localhost', port=6379, db=1)
    ref_time = r.get('ref_time')
    if not ref_time:
        ref_time = app.config['SYNC_START']

    ref_time = int(ref_time)

    posts = fb.get_recent_feed(ref_time)

    for post in posts:
        clean_post = dict()
        clean_post['post_id'] = post['id']
        clean_post['summary'] = post.get('message', "")

        temp_likes = post.get('likes', 0)
        if not temp_likes:
            clean_post['count_likes'] = 0 
        else:
            clean_post['count_likes'] = int(post['likes']['summary']['total_count'])

        temp_comments = post.get('comments', 0)
        if not temp_comments:
            clean_post['count_comments'] = 0
        else:
            clean_post['count_comments'] = int(post['comments']['summary']['total_count'])

        clean_post['link'] = post['actions'][0]['link']
        clean_post['author'] = post['from']['name']
        clean_post['author_id'] = post['from']['id']
        clean_post['created'] = calendar.timegm(time.strptime(post['created_time'], 
                                                fb.fb_time_format)
                                               )
        print clean_post['created'], '!!!!!!!!!!!!'
        clean_post['ext_link'] = post.get('link', '')
        clean_post['ref_time'] = ref_time

        update_score.delay(clean_post)
        
    # give processing time.... by 20?
    r.set('ref_time', int(time.time())-20)

"""
utils
"""
def hotness(likes, comments, created):
    t = int(created) - int(app.config['SYNC_START'])
    score = likes + comments*0.3 # comment is weighed much less
    if score == 0:
        return score, math.log10(1) + (t)/45000
    print 'diff:' + str(t)
    return score, math.log10(score) + (t)/45000


def update_or_create_post(post_id, summary, count_likes, 
                          count_comments, link, score, hot,
                          author, author_id, created, ext_link):
    obj = Post.query.filter_by(id=post_id).first()
    if obj:
        # update
        obj.count_likes = count_likes
        obj.count_comments = count_comments
        obj.score = score
        obj.summary = summary
        print hot
        obj.hot = hot
        db.session.add(obj)
        db.session.commit()
        return True
    else:
        # create obj
        obj = Post(id=post_id, summary=summary, count_likes=count_likes,
                   count_comments=count_comments, link=link,
                   score=score, hot=hot, author=author, author_id=author_id,
                   created=created, ext_link=ext_link)

        db.session.add(obj)
        db.session.commit()
        return True

"""
FRONTEND
"""
@app.route('/')
def index():
    fb = FBGroupFeed(group_id = app.config['GROUP_ID'],
                     app_id = app.config['APP_ID'],
                     app_secret = app.config['APP_SECRET'])

    trend_20 = Post.query.order_by(Post.hot.desc()).limit(20)
    return render_template("index.html", page_title='trending now', posts=trend_20)

@app.route('/top')
def top():
    fb = FBGroupFeed(group_id = app.config['GROUP_ID'],
                     app_id = app.config['APP_ID'],
                     app_secret = app.config['APP_SECRET'])

    top_50 = Post.query.order_by(Post.score.desc()).limit(50)
    return render_template("index.html", page_title='top 50',posts=top_50)

@app.route('/admin/' + app.config['SECRET'] + '/init')
def init_db():
    sync_init()
    return 'hello world'
    

@app.route('/about')
def about():
    return render_template('about.html')
    



