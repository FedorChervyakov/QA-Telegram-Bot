'''
Copyright (c) 2017 Fedor Chervyakov, Daniel Chentyrev

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
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram import ParseMode

from time import time, sleep
from datetime import datetime, timedelta
from functools import wraps
import logging
from logging.handlers import RotatingFileHandler
import re
import json
import codecs
import os
import sys
from threading import Thread, Event
import pickle

from qa_data.database import Database

'''
    Logging configuration
'''
_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

fh = RotatingFileHandler('telegram_bot.log',maxBytes=8192)
fh.setLevel(logging.INFO)
fh.setFormatter(logging.Formatter(_format))

sh = logging.StreamHandler()

logging.basicConfig(format=_format,level=logging.INFO,handlers=[fh,sh])

logger = logging.getLogger(__name__)
'''
    SOME USEFUL CONSTANTS
'''
START_TEXT = ('To upload a file, send it here and then follow my instructions. Only admins can schedule file uploads! '
             +'To ask a question start by sending /topics command') 
DOWNLOAD_FILE_TEXT = ('You have uploaded file to the server. Your next step is ' 
                    + 'to set the publication date. Please use the following format: ' 
                    + 'hh:mm dd Month yyyy')
DATE_FORMAT_ERR_TEXT = 'You are using incorrect formatting. TRY AGAIN. Your reply should look like this: 4:20 26 December 2017'

# Reading token from secret file
with open('.secret/TOKEN','r') as f:
    TOKEN = f.read()[:-1]

# Channel related constants
CHANNEL_ID = -1001100253926
CHANNEL_INVITE_LINK = 'https://t.me/joinchat/AAAAAEGUiubGLELh-MwPWA'

# List of users who can schedule uploads in the channel
LIST_OF_ADMINS = [219630622,392783281]

# Paths to various data
backup_folder = 'backup'
if backup_folder not in os.listdir():
    os.makedirs(backup_folder, exist_ok=True)

CONVERSATIONS_PATH = os.path.join(backup_folder,'conversations')
USERDATA_PATH = os.path.join(backup_folder,'user_data')
JOBS_PICKLE = os.path.join(backup_folder,'job_tuples.pickle')
DATABASE_PATH = os.path.join('qa_data','questions.db')

# ConversationHandler states
# This one is for file upload and scheduling
SCHEDULE = range(1)
# These ones are for question search 
SELECT_TOPIC, FIND_QUESTIONS, SELECT_QUESTION = range(3)

MONTHS = {'January': 1, 'February': 2, 'March': 3,'April': 4,'May': 5,'June': 6,
            'July': 7,'August': 8,'September': 9,'October': 10,'November': 11, 'December': 12}

date_pattern = re.compile('^(\d\d?):(\d\d?) (\d\d?) (January|February|March' 
                            + '|April|May|June|July|August|September'
                            + '|October|November|December) (\d\d\d\d)$') 

TOPICS_KEYBOARD = [['1','2','3'],['4','5','6'],
                      ['7','8','9'],['10','Cancel']]

db = Database(DATABASE_PATH)

TOPIC_NAMES = db.get_unique_topics()

updater = Updater(TOKEN)
dispatcher = updater.dispatcher
job_queue = updater.job_queue

def restricted(func):
    ''' Wrapper that restricts access to specified function.
    '''
    @wraps(func)
    def wrapped(bot,update,*args,**kwargs):
        user_id = update.effective_user.id
        if user_id not in LIST_OF_ADMINS:
            logger.warning("Unauthorized access denied for {0}.".format(user_id))
            return
        return func(bot, update, *args, **kwargs)
    return wrapped

def start(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text=START_TEXT)

@restricted
def download_file(bot, update, user_data):
    ''' Saves file on the hard drive.
    '''    
    if update.message.photo:
        photo = update.message.photo[-1]
        file_id = photo['file_id']
        file_name = file_id
        user_data['file_name'] = 'photo' 
    elif update.message.document:
        file_name = update.message.document.file_name
        file_id = update.message.document.file_id
        user_data['file_name'] = file_name
    newFile = bot.get_file(file_id)
    newFile.download(custom_path=(os.path.join('downloaded_data',file_name)))
    user_data['file_id'] = file_id
    logger.info('File %s downloaded.' % file_id)
    bot.send_message(chat_id=update.message.chat_id,text=DOWNLOAD_FILE_TEXT)
    return SCHEDULE

def publish_file(bot,job):
    logger.debug('Publish file job context: %s' % job.context)
    logger.info('Sending file {0} to the channel.'.format(job.context))
    try:
        bot.send_document(chat_id=CHANNEL_ID, document=job.context)
    except:
        bot.send_photo(chat_id=CHANNEL_ID,photo=open(os.path.join('downloaded_data',job.context),'rb'))

@restricted
def schedule(bot,update,job_queue,user_data):
    text = update.message.text
    logger.info('User {0} replied: {1}'.format(update.effective_user.id,text))
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

def topics(bot,update):
    reply = 'Please select a topic by typing corresponding number.\n'
    n = range(1,len(TOPIC_NAMES) + 1)
    reply_list = list(map(lambda i,t: '{0}. {1}'.format(i,t),n,TOPIC_NAMES))
    reply += '\n'.join(reply_list)
    reply_markup = ReplyKeyboardMarkup(TOPICS_KEYBOARD)
    bot.send_message(chat_id=update.message.chat_id,text=reply,
                             reply_markup=reply_markup)
    return SELECT_TOPIC

def cancel_topics(bot,update):
    update.message.reply_text('Canceling topic selection.',reply_markup=ReplyKeyboardRemove())
    return -1

def find_questions(bot,update,user_data):
    text = update.message.text
    logger.debug(text)
    match = re.match('(\d+)\.?',text)
    if match:
        choice = int(match.group())
        if 0 < choice < (len(TOPIC_NAMES) + 1):
            selected_topic = TOPIC_NAMES[choice-1]
            logger.info('User {0} selected topic {1}'.format(update.effective_user.id,selected_topic))
            user_data['topic'] = selected_topic

            reply = 'You selected topic <b>{0}</b>.\nNext, please type in your search query'.format(selected_topic)
            bot.send_message(chat_id=update.message.chat_id,text=reply,
                            reply_markup=ReplyKeyboardRemove(), parse_mode=ParseMode.HTML)
            return FIND_QUESTIONS
        else:
            bot.send_message(chat_id=update.message.chat_id,text='Invalid number, try again!')
            return SELECT_TOPIC
    else:
        bot.send_message(chat_id=update.message.chat_id,text='Please enter a number!')
        return SELECT_TOPIC

#BTW naming here is fucked up 
def show_questions(bot,update,user_data):
    text = update.message.text
    logger.debug(text)
    questions = db.search_questions(user_data['topic'],text)
    if not questions:
        bot.send_message(chat_id=update.message.chat_id,
                        text='Your search did not match any questions. Try again!')
        return FIND_QUESTIONS
    
    logger.info('User {0} requested {1}'.format(update.effective_user.id,text))
    user_data['search_s'] = text
    q = [a[0] for a in questions]
    if len(q) is 1:
        update.message.text = '1'
        show_answer(bot,update,user_data)    
        return -1
    for i in range(1,len(q)+1):
        q[i-1] = '{0}. {1}'.format(i,q[i-1])
    qs = '\n'.join(q)
    reply = ('<b>Topic:</b> {0}\nSelect a question by typing ' 
            + 'corresponding number.\n<b>Questions:</b>\n{1}').format(user_data['topic'], qs)
    bot.send_message(chat_id=update.message.chat_id,text=reply,
                    reply_markup=ReplyKeyboardRemove(),
                    parse_mode=ParseMode.HTML)
    return SELECT_QUESTION

def show_answer(bot,update,user_data):
    text = update.message.text
    match = re.match('(\d+)\.?',text)
    if match:
        choice = int(match.group(0))
        topic = user_data['topic']
        questions = db.search_questions(user_data['topic'],user_data['search_s'])
        logger.debug(questions)
        
        if 0 < choice < len(questions)+1:
            question = questions[choice-1][0]
            question_id = questions[choice-1][1]
            answer = db.find_answers(question_id)
            a = '\n'.join(answer)
            reply = '<b>Topic:</b> {0}\n<b>Q:</b> {1}\n<b>A:</b> {2}'.format(topic,question,a)
            bot.send_message(chat_id=update.message.chat_id,
                            text=reply,reply_markup=ReplyKeyboardRemove(),
                            parse_mode=ParseMode.HTML)
        else:
            update.message.reply_text('Invalid number, try again!')
            return SELECT_QUESTION
    else:
        update.message.reply_text('Please enter a number!')
        return SELECT_QUESTION
    return -1

def channel(bot,update):
    update.message.reply_text(CHANNEL_INVITE_LINK)

def fb(bot,update,user_data):
    del user_data
    return -1

def load_jobs(jq):
    now = time()

    with open(JOBS_PICKLE,'rb') as fp:
        while True:
            try:
                next_t, job = pickle.load(fp)
            except EOFError:
                break # Loaded all job tuples

            # Create threading primitives
            enabled = job._enabled
            removed = job._remove
            job._enabled = Event()
            job._remove = Event()
            if enabled:
                job._enabled.set()
            if removed:
                job._remove.set()
            next_t -= now  # Convert from absolute to relative time
            jq.run_once(job, next_t)

def save_jobs(jq):
    job_tuples = jq.queue.queue

    with open(JOBS_PICKLE, 'wb') as fp:
        for next_t, job in job_tuples:
            # Back up objects
            _job_queue = job._job_queue
            _remove = job._remove
            _enabled = job._enabled

            # Replace un-pickleable threading primitives
            job._job_queue = None  # Will be reset in jq.put
            job._remove = job.removed  # Convert to boolean
            job._enabled = job.enabled  # Convert to boolean
            # Pickle the job
            pickle.dump((next_t, job), fp)
            # Restore objects
            job._job_queue = _job_queue
            job._remove = _remove
            job._enabled = _enabled


def save_jobs_job(bot,job):
    save_jobs(job.job_queue)

def loadData(conv_handler):
    try:
        with open(CONVERSATIONS_PATH, 'rb') as f:
            conv_handler.conversations = pickle.load(f)
        with open(USERDATA_PATH,'rb') as f:
            dispatcher.user_data = pickle.load(f)
    except FileNotFoundError:
        logger.error("Data file not found")
    except:
        logger.error(repr(sys.exc_info()[0]))

def saveData(conv_handler):
    while True:
        sleep(60)

        resolved = dict()
        for k, v in conv_handler.conversations.items():
            if isinstance(v, tuple) and len(v) is 2 and isinstance(v[1], Promise):
                try:
                    new_state = v[1].result()
                except:
                    new_state = v[0]
                resolved[k] = new_state
            else:
                resolved[k] = v

        try:
            with open(CONVERSATIONS_PATH, 'wb+') as f:
                pickle.dump(resolved, f)
            with open(USERDATA_PATH, 'wb+') as f:
                pickle.dump(dispatcher.user_data, f)
        except:
            logger.exception(sys.exc_info()[0])

def stop_and_restart():
    updater.stop()
    os.execl(sys.executable, sys.executable, *sys.argv)

def restart(bot,update):
    update.message.reply_text('Bot is restarting...')
    logger.info('Bot is restarting.')
    Thread(target=stop_and_restart).start()

def error(bot,update,error):
    logger.exception('Update "%s" caused error "%s"',update,error)

def main():
    
    start_handler = CommandHandler('start',start)
    channel_handler = CommandHandler('channel',channel)
    
    # Handling file schedule conversation below
    download_handler = MessageHandler(Filters.document | Filters.photo, download_file, pass_user_data=True)
    schedule_handler = MessageHandler(Filters.text,schedule,pass_job_queue=True,pass_user_data=True)
    upload_handler = ConversationHandler(
            entry_points=[download_handler],
            states={
                SCHEDULE : [schedule_handler]},
            fallbacks=[CommandHandler('cancel',fb,pass_user_data=True)])
    
    # Handling question search here
    topics_handler = CommandHandler('topics',topics)
    qa_handler = ConversationHandler(
            entry_points=[topics_handler],
            states={
                SELECT_TOPIC : [RegexHandler('^(Cancel)$',cancel_topics),
                                MessageHandler(Filters.text,find_questions,pass_user_data=True)],
                FIND_QUESTIONS : [MessageHandler(Filters.text, show_questions, pass_user_data=True)],
                SELECT_QUESTION : [MessageHandler(Filters.text, show_answer, pass_user_data=True)]},
            fallbacks=[CommandHandler('cancel',fb,pass_user_data=True)])
    
    # Loading data from handler backups
    # and starting saveData threads.
    loadData(upload_handler)
    loadData(qa_handler)
    thrd1 = Thread(target=saveData,args=[qa_handler]).start()
    thrd2 = Thread(target=saveData,args=[upload_handler]).start()

    # Adding message handlers specified above to dispatcher 
    dispatcher.add_handler(CommandHandler('r',restart,filters=Filters.user(username='@theodor3k')))
    dispatcher.add_handler(qa_handler)
    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(channel_handler)
    dispatcher.add_handler(upload_handler) 
    dispatcher.add_error_handler(error)
    
    job_queue.run_repeating(save_jobs_job,timedelta(minutes=1))
    try: 
        load_jobs(job_queue)

    except FileNotFoundError:
        pass

    updater.start_polling()
    updater.idle()
    
    # Saving jobs after proper shutdown.
    save_jobs(job_queue)

if __name__ == '__main__':
    main()
