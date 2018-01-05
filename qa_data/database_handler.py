
import logging
import sqlite3 as lite
import sys

logging.basicConfig(level='INFO')

class Database(object):
    
    def _create_tables(self): 
        with lite.connect(self.PATH) as conn:
            cur = conn.cursor()
            cur.execute('''CREATE TABLE IF NOT EXISTS questions
                        (ID INTEGER PRIMARY KEY AUTOINCREMENT,
                        group_id TEXT, author TEXT, question TEXT)''')
            cur.execute('''CREATE TABLE IF NOT EXISTS answers
                        (question_id INTEGER, answer TEXT)''')   
            self.logger.info(cur.fetchone())


    def __init__(self,database):
        ''' Constructor for question database.
            @database is path to database file
        '''
        self.PATH = database
        self.logger = logging.getLogger(__name__)
        self._create_tables()

if __name__ == '__main__':
    db = Database('questions.db')

