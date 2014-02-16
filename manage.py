from flask.ext.script import Manager
import fboard

manager = Manager(fboard.app)

@manager.command
def initdb():
    """
    creates database tables
    """
    print 'Using databse %s' % fboard.db.engine.url
    fboard.db.create_all()
    print 'created tables'

if __name__ == '__main__':
    manager.run()
