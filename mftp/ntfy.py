import re
import logging
import requests
from bs4 import BeautifulSoup as bs
from endpoints import NOTICE_CONTENT_URL
from env import NTFY_BASE_URL, NTFY_TOPIC
from notice import update_lsni, has_idx_mutated

def ntfy_priority(subject):
    match subject:
        case 'Urgent':
            priority="5"
        case _:
            priority="3"
    
    return priority

def format_notice(notices, session):
    if notices: print('[FORMATTING NOTIFICATIONS]', flush=True)

    notifications=[]
    for notice in reversed(notices):
        id_, year = notice['UID'].split('_')

        try:
            data = parseBody(notice, session, year, id_)
            body, links = parseLinks(data, id_)
        except Exception as e:
            logging.error(f" Failed to parse notification body ~ {str(e)}")

        priority = ntfy_priority(subject=notice['Subject'])

        notifications.append({
            "Title":  f"#{id_} | {notice['Type']} | {notice['Subject']} | {notice['Company']}",
            "Body": body,
            "Tags": f"{notice['Type']}, {notice['Subject']}, {notice['Company']}",
            "Priority": priority,
            "Links": links
        })
  
    return notifications

def send(notifications, lsnif, notices):
    if notifications:
        print("[SENDING NOTIFICATIONS]", flush=True)

        for i, notification in enumerate(notifications, 1):
            if has_idx_mutated(lsnif, notices, i): break

            try:
                requests.post(f"{NTFY_BASE_URL}/${NTFY_TOPIC}",
                    data=notification["Body"],
                    headers={
                                "Title": notification["Title"],
                                "Tags": notification["Tags"],
                                "Priority": notification["Priority"],
                                "Icon": "https://miro.medium.com/v2/resize:fit:600/1*O94LHxqfD_JGogOKyuBFgA.jpeg",
                                "Action": notification["Links"]
                    })
                update_lsni(lsnif, notices, i)
                logging.info(f" [NOTIFICATION SENT] ~ {notification['Title']}")
            except Exception as e:
                logging.error(f" Failed to send notification: {notification['Title']} ~ {str(e)}")

def parseBody(notice, session, year, id_):
    content = session.get(NOTICE_CONTENT_URL.format(year, id_))
    content_html = bs(content.text, 'html.parser')
    content_html_div = bs.find_all(content_html, 'div', {'id': 'printableArea'})[0]

    body = ''
    for br in content_html_div.find_all('br'):
        body = body + br.next_sibling.strip() + '\n'

    body = body + notice['Time']

    return body

def parseLinks(data, id_):
    body = data
    links = re.findall(r'(https?://[^\s]+)', data)
    links = list(set(result.lower() for result in links))
    action_template = "view, Link {}, {}"
    actions = ""

    for i, link in enumerate(links, 1):
        if i == 4: break
        elif i > 1: actions = actions + "; "

        body = body.replace(link, f'<LINK {i}>')
        template = action_template
        actions = actions + template.format(i, link)

    return body, actions
