import os
from dotenv import load_dotenv
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import traceback
from flask import Flask, request
from celery import Celery
import logging
from datetime import datetime
import re
 

load_dotenv()

app = Flask(__name__)
celery = Celery('tasks', broker='pyamqp://guest@localhost//')

 
 
log_file = '/var/log/messaging_system.log'
logging.basicConfig(filename=log_file, level=logging.INFO)

@celery.task(name='tasks.send_email')
def send_email(recipient):
    print(f"Attempting to send email to {recipient}")
    logging.info(f"Attempting to send email to {recipient}")
    try:
        smtp_server = 'live.smtp.mailtrap.io'
        port = 2525
        username = 'api'
        password = os.getenv('MAILTRAP_API_TOKEN', '77ba485ac265a42d5d61dc85735769ce')

        msg = MIMEMultipart('alternative')
        msg['Subject'] = "Awesome HNG!"
        msg['From'] = "Magic Elves <mailtrap@demomailtrap.com>"
        msg['To'] = recipient

        text = "Congrats for sending email don send"
        html = """
        <!doctype html>
        <html>
        <head>
            <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
        </head>
        <body>
            <p>Congrats email don send</p>
        </body>
        </html>
        """

        part1 = MIMEText(text, 'plain')
        part2 = MIMEText(html, 'html')

        msg.attach(part1)
        msg.attach(part2)

        logging.info(f"Connecting to SMTP server: {smtp_server}:{port}")
        with smtplib.SMTP(smtp_server, port, timeout=30) as server:
            logging.info("Starting TLS")
            server.starttls()
            logging.info("Logging in")
            server.login(username, password)
            logging.info("Sending email")
            server.sendmail(msg['From'], recipient, msg.as_string())

        print(f"Email sent successfully to {recipient}")
        logging.info(f"Email sent successfully to {recipient}")
    except (smtplib.SMTPException, IOError) as e:
        error_message = f"Failed to send email to {recipient}. Error: {str(e)}\n{traceback.format_exc()}"
        print(error_message)
        logging.error(error_message)
        raise send_email.retry(exc=e, countdown=60)  # Retry after 60 seconds
    except Exception as e:
        error_message = f"Unexpected error when sending email to {recipient}. Error: {str(e)}\n{traceback.format_exc()}"
        print(error_message)
        logging.error(error_message)
        raise


def is_valid_email(email):
    # Regular expression for validating an email
    regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(regex, email)

@app.route('/')
def index():
    if 'sendmail' in request.args:
        recipient = request.args.get('sendmail')
        if is_valid_email(recipient):
            try:
                send_email.delay(recipient)
                return f"Email queued for sending to {recipient}"
            except Exception as e:
                return f"Failed to send email: {str(e)}", 500
        else:
            return "Invalid email format", 400
    elif 'talktome' in request.args:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logging.info(f"Talktome request at {current_time}")
        return f"Logged at {current_time}"
    else:
        return "Use ?sendmail or ?talktome parameters"
    
@app.route('/logs')
def get_logs():
    try:
        with open(log_file, 'r') as f:
            logs = f.read()
        return logs, 200, {'Content-Type': 'text/plain; charset=utf-8'}
    except Exception as e:
        return f"Failed to retrieve logs: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=True)
