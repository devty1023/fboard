import unittest
import tempfile
import fboard
import os
import time
import datetime
import calendar

class DBTest(unittest.TestCase):
    def setUp(self):
        self.db_fd, fboard.app.config['SQLALCHEMY_DATABASE'] \
                = tempfile.mkstemp()
        fboard.db.create_all()

    def tearDown(self):
        os.close(self.db_fd)
        os.unlink(fboard.app.config['SQLALCHEMY_DATABASE'])

class FBTest(unittest.TestCase):
    def setUp(self):
        self.fb = fboard.FBGroupFeed(fboard.app.config['GROUP_ID'],
                                     fboard.app.config['APP_ID'],
                                     fboard.app.config['APP_SECRET'],
                                     )
    def test_get_feed(self):
        feed = self.fb.get_feed(limit=1)
        #print 'number of entries: ',len(feed)
        for key in feed[0]:
            print key
        assert feed

    def test_get_more_feed(self):
        self.fb.get_feed(limit=1)
        feed = self.fb.get_more_feed()
        #print 'number of entries: ',len(feed)
        assert feed

    def test_get_recent_feed(self):
        now = int(time.time())
        today = calendar.timegm(datetime.datetime(2014, 02, 15, 0, 0).timetuple())
        all_time = 0

        now_feed = self.fb.get_recent_feed(now, limit=10)
        #print "now feed: ", len(now_feed)
        assert not now_feed

        today_feed = self.fb.get_recent_feed(today, limit=10)
        #print "today feed: ", len(today_feed)
        assert today_feed

        all_feed = self.fb.get_recent_feed(all_time, limit=10)
        #print "all feed: ", len(all_feed)
        assert all_feed

    def test_get_comments(self):
        mock_id = '174499879257223_719016674805538'
        wrong_id = '174499879257223_7190166748055381'

        assert self.fb.get_comments(mock_id)
        assert not self.fb.get_comments(wrong_id)

    def tearDown(self):
        pass
if __name__ == '__main__':
    unittest.main()

