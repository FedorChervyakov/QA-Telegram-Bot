
from qa_data.spreadsheet_api import API, parse_questions

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


    def __init__(self,database):
        ''' Constructor for question database.
            @database is path to database file
        '''
        self.PATH = database
        self.logger = logging.getLogger('Database')
        self._create_tables()
    
    def add_question(self, question_d):
        try:
            with lite.connect(self.PATH) as conn:
                c = conn.cursor()
                c.execute("INSERT INTO questions VALUES (NULL,?,?,?,?)",
                          (question_d['topic'],question_d['group'],
                              question_d['author'],question_d['question']))
                c.execute('''SELECT ID FROM questions WHERE question = ? 
                         AND author = ? AND group_id = ?''', (question_d['question'],
                         question_d['author'], question_d['group']))
                _id = c.fetchone()[0]
                for a in question_d['answers']:
                    c.execute("INSERT INTO answers VALUES (?,?)",(_id,a))
        except Exception as e:
            self.logger.exception(e)
    
    def find_questions(self, topic, search_query):
        self.logger.info('Search query: {0} Topic: {1}'.format(search_query,topic))
        try: 
            with lite.connect(self.PATH) as conn:
                c = conn.cursor()
                c.execute('''SELECT question, ID FROM questions WHERE
                          topic = ? AND question LIKE ? ORDER BY ID''', (topic,'%' + search_query + '%'))
                questions = c.fetchall()
                self.logger.debug(questions)
                return questions
        except Exception as e:
            self.logger.exception(e)

    def find_answers(self,question_id):
        self.logger.info('Finding answer for question {0}'.format(question_id))
        try:
            with lite.connect(self.PATH) as conn:
                c = conn.cursor()
                c.execute("SELECT answer FROM answers WHERE question_id = ?",(question_id,))
                answers = c.fetchall()
                if not answers:
                    raise Exception('Invalid question id.')
                else:
                    return [a[0] for a in answers]
        except Exception as e:
            self.logger.exception(e)

    def get_unique_topics(self):
        try:
            with lite.connect(self.PATH) as conn:
                c = conn.cursor()
                c.execute('SELECT DISTINCT topic from questions')
                topics = sorted([str(t[0]) for t in c.fetchall()])
                self.logger.debug(topics)
                return topics
        except Exception as e:
            self.logger.exception(e)

