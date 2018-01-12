
import logging
import sqlite3 as lite
import sys
from functools import reduce

def tokenize_question(question):
    q_list = question.split(' ')
    tokens = [s[:-2] if len(s) > 4 else s for s in q_list]
    return [t.lower() for t in tokens]

class Database(object):
    
    def _create_tables(self): 
        with lite.connect(self.PATH) as conn:
            cur = conn.cursor()
            cur.execute('''CREATE TABLE IF NOT EXISTS questions
                        (ID INTEGER PRIMARY KEY AUTOINCREMENT, topic TEXT,
                        group_id TEXT, author TEXT, question TEXT)''')
            cur.execute('''CREATE TABLE IF NOT EXISTS answers
                        (question_id INTEGER, answer TEXT)''')   
            cur.execute('''CREATE TABLE IF NOT EXISTS tokens
                        (question_ID INTEGER, token TEXT)''')
 

    def __init__(self,database):
        ''' Constructor for question database.
            @database is path to database file
        '''
        self.PATH = database
        self.logger = logging.getLogger('Database')
        self._create_tables()

    def clear_tables(self):
        with lite.connect(self.PATH) as conn:
            c = conn.cursor()
            c.execute("DELETE FROM questions")
            c.execute("DELETE FROM answers")
            c.execute("VACUUM;")


    def index_questions(self):
        with lite.connect(self.PATH) as conn:
            c = conn.cursor()
            c.execute('select question,ID from questions')
            questions = c.fetchall()
            self.logger.info('There are {0} questions in the database.'.format(len(questions)))
            for q in questions:
                if q is None: 
                    break
                tokens = tokenize_question(q[0])
                q_id = [q[1]] * len(tokens)
                t = zip(q_id,tokens)
                self.logger.debug('Tokenizing question number {0} to {1}'.format(q[1],', '.join(tokens)))
                c.executemany("INSERT INTO tokens VALUES (?,?)", (t))
                                               
    
    def add_question(self, question_d):
        ''' This function is used only with spreasheet_api module.
        ''' 
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
    
    def search_questions(self,topic, search_query):
        self.logger.info('Searching for {0}. Topic is {1}'.format(search_query, topic))
        tokens = tokenize_question(search_query)
        try:
            with lite.connect(self.PATH) as conn:
                c = conn.cursor()
                ids = list()
                for t in tokens:
                    sql_query = '''
                            select distinct questions.ID
                            from questions
                            inner join tokens on questions.ID=tokens.question_id
                            where questions.topic=? and tokens.token like ?'''
                    c.execute(sql_query,(topic,'%' + t + '%'))
                    ids.append([q[0] for q in c.fetchall()])   
                
                qids = list()
                if len(ids) is 1:
                    qids = ids[0]
                elif len(ids) > 1:
                    qids = list(reduce(lambda t,l: set(t).intersection(l),ids))
                
                qids_s = ', '.join('?' for _ in qids)
                sql_query_q = "select question, ID from questions where ID in ({0})".format(qids_s)

                c.execute(sql_query_q, qids)
                return  c.fetchall()

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

