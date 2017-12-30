'''
Copyright (c) 2017 Fedor Chervyakov, Daniil Chentyrev

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.'''

from telegram.ext import Updater
from telegram.ext import CommandHandler, MessageHandler, ConversationHandler
from telegram.ext import Filters, RegexHandler

from datetime import datetime
from functools import wraps
import logging
import re
import json
import codecs

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                            level=logging.INFO)
logger = logging.getLogger(__name__)


START_TEXT = ('To upload a file, send it here and then follow my instructions. Only admins can schedule file uploads! '
             +'To ask a question start by sending /topics command') 
DOWNLOAD_FILE_TEXT = ('You have uploaded file to the server. Your next step is ' 
                    + 'to set the publication date. Please use the following format: ' 
                    + 'hh:mm dd Month yyyy')
DATE_FORMAT_ERR_TEXT = 'You are using incorrect formatting. TRY AGAIN. Your reply should look like this: 4:20 26 December 2017'

TOKEN = '427077063:AAE52Z42kce-qFSa6Vw9UZcs0CMHAGbc_UQ'
CHANNEL_ID = -1001100253926

LIST_OF_ADMINS = [219630622,392783281]

SCHEDULE = range(1)
SELECT_TOPIC, SELECT_QUESTION = range(2)

MONTHS = {'January': 1, 'February': 2, 'March': 3,'April': 4,'May': 5,'June': 6,
            'July': 7,'August': 8,'September': 9,'October': 10,'November': 11, 'December': 12}

date_pattern = re.compile('^(\d\d?):(\d\d?) (\d\d?) (January|February|March' 
                            + '|April|May|June|July|August|September'
                            + '|October|November|December) (\d\d\d\d)$') 

TOPIC_NAMES = ['Налоги', 'Бюджет', 'Политика', 'Рынки', 'Организации']

#Building question database
qa_filename = 'sample_questions.json'
qas = dict()
for n in TOPIC_NAMES:
    qas[n] = list()

with codecs.open(qa_filename,'rU','utf-8') as f:
    parsed_json = json.load(f)
    for q in parsed_json:
        qas[q[0]].append((q[1],q[2]))
logger.info(qas)

updater = Updater(TOKEN)
dispatcher = updater.dispatcher
job_queue = updater.job_queue

def restricted(func):
    @wraps(func)
    def wrapped(bot,update,*args,**kwargs):
        user_id = update.effective_user.id
        if user_id not in LIST_OF_ADMINS:
            self.logger.warning("Unauthorized access denied for {}.".format(user_id))
            return
        return func(bot, update, *args, **kwargs)
    return wrapped

def start(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text=START_TEXT)

@restricted
def download_file(bot, update, user_data):
    file_id = update.message.document.file_id
    file_name = update.message.document.file_name
    newFile = bot.get_file(file_id)
    newFile.download(custom_path=('data/' + file_name))
    user_data['file_name'] = file_name
    user_data['file_id'] = file_id
    logger.info('File %s downloaded.' % file_id)
    logger.debug('Original filename is %s' % file_name)
    bot.send_message(chat_id=update.message.chat_id,text=DOWNLOAD_FILE_TEXT)
    return SCHEDULE

def publish_file(bot,job):
    logger.info('publish file job context: %s' % job.context)
    bot.send_document(chat_id=CHANNEL_ID, document=job.context)

def error(bot, update, error):
    logger.warn('Update "%s" caused error "%s"' % (update, error))

@restricted
def schedule(bot,update,job_queue,user_data):
    text = update.message.text
    logging.info('User {0} replied: {1}'.format(update.effective_user.id,text))
    m = re.match(date_pattern,text)
    logger.info(text)
    if m:
        dt = datetime(int(m.group(5)),MONTHS[m.group(4)],int(m.group(3)),hour=int(m.group(1)),minute=int(m.group(2)))
        job_queue.run_once(publish_file,dt,context=user_data['file_id'])
        update.message.reply_text('You have scheduled %s to upload on %s' % (user_data['file_name'],dt))
        return -1
    else:
        update.message.reply_text(DATE_FORMAT_ERR_TEXT)
        return SCHEDULE

def topics(bot,update,user_data):
    reply = 'Please select a topic by typing corresponding number.\n'
    i = 1
    for topic in TOPIC_NAMES:
        reply += ('{0}. {1}\n'.format(i,topic))
        i += 1
    bot.send_message(chat_id=update.message.chat_id,text=reply)
    return SELECT_TOPIC

def show_questions(bot,update,user_data):
    text = update.message.text
    logging.debug(text)
    match = re.match('(\d+)\.?',text)
    reply = ''
    if match:
        choice = int(match.group())
        if choice < (len(TOPIC_NAMES) + 1) and choice > 0:
            selected_topic = TOPIC_NAMES[int(text)-1]
            logging.info('User {0} selected topic {1}'.format(update.effective_user.id,selected_topic))
            user_data['topic'] = selected_topic
            questions = [q[0] for q in qas[selected_topic]]
            for i in range(1,len(questions)+1):
                questions[i-1] = '{0}. {1}'.format(i,questions[i-1])
            qs = '\n'.join(questions)
            reply = 'Topic: {0}\nSelect a question by typing corresponding number.\nQuestions:\n{1}'.format(selected_topic, qs)
        else:
            bot.send_message(chat_id=update.message.chat_id,text='Invalid number, try again!')
            return SELECT_TOPIC
    else:
        bot.send_message(chat_id=update.message.chat_id,text='Please enter a number!')
        return SELECT_TOPIC
    bot.send_message(chat_id=update.message.chat_id, text=reply)
    return SELECT_QUESTION

def show_answer(bot,update,user_data):
    text = update.message.text
    match = re.match('(\d+)\.?',text)
    if match:
        choice = int(match.group())
        topic = user_data['topic']
        if choice > 0 and choice < len(qas[topic])+1:
            qa = qas[topic][choice-1]
            a = '\n'.join(qa[1])
            reply = 'Topic: {0}\nQ: {1}\nA: {2}'.format(topic,qa[0],a)
            bot.send_message(chat_id=update.message.chat_id,text = reply) 
        else:
            update.reply_text('Invalid number, try again!')
            return SELECT_QUESTION
    else:
        bot.reply_text('Please enter a number!')
    return -1

def fb(bot,update,user_data):
    del user_data
    return -1

def error(bot,update,error):
    logger.warning('Update "%s" caused error "%s"',update,error)
    update.reply_text('An internal error occured. The bot may be out of operation')

def main():
    start_handler = CommandHandler('start',start)
    download_handler = MessageHandler(Filters.document, download_file, pass_user_data=True)
    schedule_handler = MessageHandler(Filters.text,schedule,pass_job_queue=True,pass_user_data=True)
    upload_handler = ConversationHandler(
            entry_points=[download_handler],
            states={
                SCHEDULE : [schedule_handler]},
            fallbacks=[CommandHandler('cancel',fb,pass_user_data=True)])
    
    topics_handler = CommandHandler('topics',topics,pass_user_data=True)
    qa_handler = ConversationHandler(
            entry_points=[topics_handler],
            states={
                SELECT_TOPIC : [MessageHandler(Filters.text,show_questions,pass_user_data=True)],
                SELECT_QUESTION : [MessageHandler(Filters.text, show_answer, pass_user_data=True)]},
            fallbacks=[CommandHandler('cancel',fb,pass_user_data=True)])
    dispatcher.add_handler(qa_handler)
    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(upload_handler) 
    dispatcher.add_error_handler(error)
    
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
