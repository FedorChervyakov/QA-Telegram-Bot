
from database_handler import Database
from spreadsheet_handler import API, parse_questions

import logging
import sqlite3 as lite


SPREADSHEET_ID = '1L_-zGLY4IJhdKiqkooS_vMMmls1fkWN3XtUHz5lzW0A'

SHEET_NAMES = ['1. Сущность','2. Система','3. Управление','4. Налоги',
               '5. Бюджет','6. ГВФ','7. Политика','8. Рынки',
               '9. Организации','10. Международные']

logging.basicConfig(level='INFO')

with lite.connect('questions.db') as conn:
    c = conn.cursor()
    c.execute('DROP TABLE questions')
    c.execute('DROP TABLE answers')

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
    if color[2] < color[1] > color[0]:
        return 'green'
    elif color[0] == 1 and color[1] == 1 and color[2] == 1:
        return 'white'
    elif color[1] > color[2] < color[0]:
        return 'yellow'
    elif color[1] < color[0] > color[2]:
        return 'red'

def format_questions(questions):
    q = list()
    for row in questions:
        q.append(list())
        for cell in row:
            if 2 == len(cell):
                color = convert_color(cell[1])
                if None == color: logging.warn('Invalid color')
                q[-1].append([cell[0], color_to_string(color)])

            elif '' == cell:
                q[-1].append(['',None])
    return q

def build_question_dicts(formatted_questions,topic):
    qna = list()
    for row in formatted_questions:
        try:
            # checking if this is row with question title or the answer
            group = row[0][0]
            author = row[1][0]
            qn = row[3][0]
            if group != '' and author != '' and qn != '':
                qna.append({'topic': topic,'group' : group, 'author' : author, 'question' : qn, 'answers' : list()})
            elif row[3][1] == 'green':
                if row[4][0] == '':
                    qna[-1]['answers'].append(str(row[3][0]))
                else:
                    qna[-1]['answers'].append('{0} - {1}'.format(row[3][0],row[4][0]))
        except Exception as e:
            logging.error(row)
            logging.exception(e)
    return qna

def insert_questions_from_sheet(sheet,topic):
    questions = parse_questions(sheet)
    formatted_questions = format_questions(questions)
    q_list = build_question_dicts(formatted_questions,topic)
    for q in q_list:
        if len(q['answers']) == 0: 
            logging.warn('Could not find the answers for question by {0} from group {1}'.format(q['author'],q['group'])) 
            continue
        db.add_question(q)

def main():
    api = API()
    
    for sheet in SHEET_NAMES:
        ranges = ['{0}!A3:E'.format(sheet)]
        spreadsheet = api.read_spreadsheet_data(SPREADSHEET_ID, ranges)
        topic = sheet[4:] if '10.' in sheet else sheet[3:]
        insert_questions_from_sheet(spreadsheet['sheets'][0],topic)

    
    

if __name__ == '__main__':
    main()
