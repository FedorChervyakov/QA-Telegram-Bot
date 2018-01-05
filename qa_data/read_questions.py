
from database_handler import Database
from spreadsheet_handler import API, parse_questions

import logging

SPREADSHEET_ID = '1L_-zGLY4IJhdKiqkooS_vMMmls1fkWN3XtUHz5lzW0A'

logging.basicConfig(level='INFO')

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

def main():
    api = API()
    spreadsheet = api.read_spreadsheet_data(SPREADSHEET_ID, ['2. Система!A3:E'])
    questions = parse_questions(spreadsheet['sheets'][0])
    topic = '2. Система'

    q = list()
    for row in questions:
        q.append(list())
        for cell in row:
            if 2 == len(cell):
                color = convert_color(cell[1])
                if not color: logging.warn('Invalid color')
                q[-1].append([cell[0], color_to_string(color)])

            elif '' == cell:
                q[-1].append(['',None])

    qna = list()
    for row in q:
        try:
            # checking if this is row with question title or the answer
            group = row[0][0]
            author = row[1][0]
            qn = row[3][0]
            if group != '' and author != '' and qn != '':
                qna.append({'topic': topic,'group' : group, 'author' : author, 'question' : qn, 'answers' : list()})
            elif row[3][1] == 'green':
                qna[-1]['answers'].append(str(row[3][0]))
        except Exception as e:
            logging.error(e)

    db = Database('questions.db') 
    for question in qna:
        if len(question['answers']) == 0: 
            logging.warn('Could not find the answers for question by {0} from group {1}'.format(question['author'],question['group'])) 
            continue
        db.add_question(question)
    
    

if __name__ == '__main__':
    main()
