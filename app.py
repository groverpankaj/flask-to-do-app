from flask import Flask, render_template, url_for, request, redirect, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import pytz
from flask_bootstrap import Bootstrap

# Google Calender
from googleapiclient.discovery import build
from oauth2client import file, client, tools
from google_auth_oauthlib.flow import InstalledAppFlow

app = Flask(__name__)
app.secret_key = 'dont tell anyone'

Bootstrap(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'

db = SQLAlchemy(app)


# Model
class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    priority = db.Column(db.Boolean, default=False)
    content = db.Column(db.String(200), nullable=False)
    finish_date = db.Column(db.DateTime, nullable=False)
    completed = db.Column(db.Boolean, default=False)
    date_created = db.Column(
        db.DateTime, default=datetime.now(pytz.timezone('US/Pacific')))

    def _repr__(self):
        return '<Task %s >' % self.content



@app.route('/',  methods=['POST', 'GET'])
def index():
    pstatus = 'all'
    return redirect('/' + pstatus)


# Index route
@app.route('/<pstatus>',  methods=['POST', 'GET'])
def indexall(pstatus):

    # New Task is submitted
    if request.method == 'POST':
        task_content = request.form['content']

        # The task content has to be more than 2 alphabets
        if (len(task_content) < 3):
            return redirect('/')

        task_date = datetime.strptime(
            request.form['finishdate'], '%m/%d/%Y %I:%M %p')
        new_task = Todo(content=task_content, finish_date=task_date)

        try:
            db.session.add(new_task)
            db.session.commit()
            flash('Task successfully added')
        except:
            flash('There was an error posting the task')

        if (pstatus == 'all'):
            return redirect('/all')
        else:
            return redirect('/onlypriority')
            
        
    else:
        # Default listing of all tasks
        today = datetime.now().__format__('%m/%d/%Y %I:%M %p')
        nowDt = datetime.now()

        if (pstatus == 'all'):
            tasks = Todo.query.order_by(Todo.finish_date).all()
        else:
            tasks = Todo.query.filter_by(priority = True).order_by(Todo.finish_date).all()

        return render_template('index.html', tasks=tasks, today=today, nowDt=nowDt, pstatus=pstatus)


@app.route('/delete/<int:id>/<pstatus>')
def delete(id, pstatus):
    task_to_delete = Todo.query.get_or_404(id)

    try:
        db.session.delete(task_to_delete)
        db.session.commit()
        flash('Task successfully deleted')
    except:
        return ("Task deletion failed")
    
    if (pstatus == 'all'):
            return redirect('/all')
    else:
        return redirect('/onlypriority')


@app.route('/edit/<int:id>/<pstatus>', methods=['POST', 'GET'])
def edit(id, pstatus):

    task_to_edit = Todo.query.get_or_404(id)

    if request.method == 'POST':

        task_to_edit.content = request.form['content']
        task_to_edit.finish_date = datetime.strptime(
            request.form['finishdate'], '%m/%d/%Y %I:%M %p')
        
        # The task content has to be more than 2 alphabets
        if (len(task_to_edit.content) < 3):
            return redirect('/edit/' + str(id))
        
        try:
            db.session.commit()
            flash('Task successfully edited')
        except:
            return ("Editing Task failed")

        if (pstatus == 'all'):
            return redirect('/all')
        else:
            return redirect('/onlypriority')

    else:
        today = datetime.now().__format__('%m/%d/%Y %I:%M %p')
        nowDt = datetime.now()
        
        if (pstatus == 'all'):
            tasks = Todo.query.order_by(Todo.finish_date).all()
        else:
            tasks = Todo.query.filter_by(priority = True).order_by(Todo.finish_date).all()

        return render_template('edit-modal.html', tasks=tasks, today=today, nowDt=nowDt, id=id, pstatus=pstatus)
    

# Change Status
@app.route('/complete/<status>/<int:id>/<pstatus>', methods=['POST', 'GET'])
def complete(status, id, pstatus):

    # status passed by addEventListener
    if (status == 'no'):
        status = False
        flash('Task successfully marked Incomplete')
    else:
        status = True
        flash('Task successfully marked Completed')

    task_to_edit = Todo.query.get_or_404(id)
    task_to_edit.completed = status

    try:
        db.session.commit()
    except:
        flash("Task status updation failed")
    
    if (pstatus == 'all'):
            return redirect('/all')
    else:
        return redirect('/onlypriority')


# Changing Priority of the task
@app.route('/priority/<status>/<int:id>/<pstatus>', methods=['GET'])
def priority(status, id, pstatus):
    
    task_to_edit = Todo.query.get_or_404(id)

    if (status == 'yes'):
        task_status = True
        flash('Task Priority has been successfully changed to High')
    else:
        task_status = False
        flash('Task Priority has been successfully changed to Low')

    task_to_edit.priority = task_status
    
    
    try:
        db.session.commit()
    except:
        return ("Task priority updation failed")

    if (pstatus == 'all'):
        return redirect('/all')
    else:
        return redirect('/onlypriority')
        
      



@app.route('/calender/<int:id>/<pstatus>')
def calender(id, pstatus):

    SCOPES = 'https://www.googleapis.com/auth/calendar'

    
    store = file.Storage('token.json')
    credentials = store.get()

    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets('client_secret.json', SCOPES)
        credentials = tools.run_flow(flow, store)


    service = build("calendar", "v3", credentials=credentials)

    result = service.calendarList().list().execute()

    calendar_id = result['items'][1]['id']

    # Event Details
    task_to_calender = Todo.query.get_or_404(id)
    task_name = task_to_calender.content
    start_time = task_to_calender.finish_date
    end_time = start_time + timedelta(hours=1)
    timezone = 'America/Los_Angeles'

    event = {
    'summary': task_name,
    # 'location': 'location',
    # 'description': 'description',
    'start': {
        'dateTime': start_time.strftime("%Y-%m-%dT%H:%M:%S"),
        'timeZone': timezone,
    },
    'end': {
        'dateTime': end_time.strftime("%Y-%m-%dT%H:%M:%S"),
        'timeZone': timezone,
    },
    'reminders': {
        'useDefault': False,
        'overrides': [
        {'method': 'email', 'minutes': 24 * 60},
        {'method': 'popup', 'minutes': 10},
        ],
    },
    }

    flash('Successfully added to Google Calender')

    service.events().insert(calendarId=calendar_id, body=event).execute()

    if (pstatus == 'all'):
        return redirect('/all')
    else:
        return redirect('/onlypriority')


if (__name__ == "__main__"):
    app.run(host='127.0.0.1', port=8080, debug=True)
