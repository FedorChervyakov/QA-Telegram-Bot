
from spreadsheet_handler import API, parse_questions

import logging
import sqlite3 as lite
import sys


class Database(object):
    
    def _create_tables(self): 
        with lite.connect(self.PATH) as conn:
            cur = conn.cursor()
            cur.execute('''CREATE TABLE IF NOT EXISTS questions
                        (ID INTEGER PRIMARY KEY AUTOINCREMENT, topic TEXT,
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
    
    def add_question(self, question_d):
        try:
            with lite.connect(self.PATH) as conn:
                c = conn.cursor()
                c.execute("INSERT INTO questions VALUES (NULL,?,?,?,?)",
                          (question_d['topic'],question_d['group'],
                              question_d['author'],question_d['question']))
                c.execute("SELECT ID FROM questions WHERE question = ?",(question_d['question'],))
                _id = c.fetchone()[0]
                for a in question_d['answers']:
                    c.execute("INSERT INTO answers VALUES (?,?)",(_id,a))
        except Exception as e:
            self.logger.exception(e)
        

def main():
    api = API()
    db = Database('questions.db')

if __name__ == '__main__':
    main()
