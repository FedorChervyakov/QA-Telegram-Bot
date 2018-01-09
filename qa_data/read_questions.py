from database import Database
from spreadsheet_api import API, parse_questions

import logging
import sqlite3 as lite
import numpy as np

RGB_COLORS_D = {'green' : (0,1,0), 'yellow' : (1,1,0), 
                'red' : (1,0,0), 'magenta' : (1,0,1),
                'blue' : (0,0,1), 'cyan' : (0,1,1),
                'white' : (1,1,1), 'black' : (0,0,0)}
SPREADSHEET_ID = '1L_-zGLY4IJhdKiqkooS_vMMmls1fkWN3XtUHz5lzW0A'

SHEET_NAMES = ['1. Сущность','2. Система','3. Управление','4. Налоги',
               '5. Бюджет','6. ГВФ','7. Политика','8. Рынки',
               '9. Организации','10. Международные']

logging.basicConfig(level='INFO')

db = Database('questions.db') 

def convert_color(color_dict):
    colors = ['red','green','blue']
    keys = color_dict.keys()
    color = []
    for c in colors:
        if c in keys: color.append(color_dict[c])
        else: color.append(0)
    return tuple(color)

def color_to_string(color):

    def distance(left,right):
        return sum((l-r)**2 for l,r in zip(left,right))**0.5

    if color[0] < color[1] > color[2]:
        return 'green'

    min_d = 10 
    min_k = 'white'
    for k,v in RGB_COLORS_D.items():
        d_color = distance(v,color)
        if d_color < min_d:
            min_d = d_color
            min_k = k
    return min_k

def format_questions(questions):
    q = list()
    for row in questions:
        q.append(list())
        for i in range(5):
            try:
                cell = row[i]
                color = convert_color(cell[1])
                q[-1].append([cell[0], color_to_string(color)])
            except IndexError:
                q[-1].append(['','white'])
    return q

def build_question_dicts(formatted_questions,topic):
    qna = list()
    for row in formatted_questions:
        try:
            group = row[0][0]
            author = row[1][0]
            qn = row[3][0]
            # checking if this is row with question title or the answer
            if group is not  '' and author is not '' and qn is not '':
                qna.append({'topic': topic,'group' : group, 'author' : author, 'question' : qn, 'answers' : list()})
            # Checking if this row is the answer (i.e. green)
            elif row[3][1] == 'green':
                # row 4 is column E in spreadsheet
                if row[4][0] == '':
                    qna[-1]['answers'].append(str(row[3][0]))
                else:
                    qna[-1]['answers'].append('{0} - {1}'.format(row[3][0],row[4][0]))
        except Exception as e:
            logging.error(row)
            logging.exception(e)
    return qna

def insert_questions_from_sheet(sheet,topic):
    logging.info('Parsing questions...')
    questions = parse_questions(sheet)
    logging.info('Formatting questions..')
    formatted_questions = format_questions(questions)
    q_list = build_question_dicts(formatted_questions,topic)
    for q in q_list:
        if len(q['answers']) == 0: 
            logging.warn('Could not find the answers for question by {0} from group {1}'.format(q['author'],q['group'])) 
            continue
        db.add_question(q)

def read_questions():
    api = API()
    db.clear_tables()
    for sheet in SHEET_NAMES:
        ranges = ['{0}!A3:E'.format(sheet)]
        spreadsheet = api.read_spreadsheet_data(SPREADSHEET_ID, ranges)
        topic = sheet[4:] if '10.' in sheet else sheet[3:]
        insert_questions_from_sheet(spreadsheet['sheets'][0],topic)



def main():
    db.index_questions()  

if __name__ == '__main__':
    main()
