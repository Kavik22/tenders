import requests, smtplib
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from time import sleep
from email.mime.text import MIMEText
from datetime import datetime
from pytz import timezone
import config

def get_template(items):
    text_start = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>Document</title>
        </head>
        <body>
        <h2 style="background-color: #A9A9A9; padding: 10px 10px 10px 20px; border-radius: 10px;">Tenders from: <a href=https://zakupki.gov.ru/epz/order/extendedsearch/results.html>zakupki.gov.ru</a></h2>
        """
    text_end = """
        </body>
        </html>
        """

    text_mid = ''
    # with open('results.json', 'r', encoding='utf-8') as file:
    #     items = json.load(file)

    for item in items:
        text_mid += f"""
            <div style="background-color: #DCDCDC; padding: 5px 20px 20px 20px; border-radius: 10px;">
            <h3><a href={item['link']}>{item['object_of_purchase']}</a></h3>
            Starting price: {item['starting_price']}<br/>
            Posting date: {item['posting_date']}<br/>
            Update date: {item['update_date']}<br/>
            Application deadline: {item['application_deadline']}</div>
            <br/>
            """

    text = text_start + text_mid + text_end
    return text


def send_email(results):
    sender = config.settings['EMAIL_ADDRESS']
    password = config.settings['EMAIL_PASSWORD']

    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()

    text = get_template(results)



    try:
        server.login(sender, password)
        msg = MIMEText(text, 'html')
        current_time = datetime.now(tz=timezone('Europe/Moscow')).strftime("%d-%m-%Y %H:%M:%S")
        msg['Subject'] = f'New tenders for {current_time}'
        server.sendmail(sender, sender, msg.as_string())
        print('Message sent!')
    except Exception as ex:
        print(f'{ex}\nCheck your login or password')


def get_tender_data(tender):
    object_of_purchase = tender.find('div', class_='registry-entry__body-value').text
    link = 'https://zakupki.gov.ru' + tender.find('div', class_='registry-entry__header-mid__number').find('a').get(
        'href')
    try:
        starting_price = tender.find('div', class_='price-block__value').text.strip().replace('\xa0', '').split(' ')[0]
    except:
        starting_price = 'No'
    dates = tender.find('div', class_='data-block mt-auto').find_all('div', class_='data-block__value')
    number = tender.find('div', class_='registry-entry__header-mid__number').text.strip().split(' ')[1]
    try:
        posting_date = dates[0].text
    except:
        posting_date = 'No'
    try:
        update_date = dates[1].text
    except:
        update_date = 'No'
    try:
        application_deadline = dates[2].text
    except:
        application_deadline = 'No'

    dict = {
        'number': number,
        'object_of_purchase': object_of_purchase,
        'link': link,
        'starting_price': starting_price,
        'posting_date': posting_date,
        'update_date': update_date,
        'application_deadline': application_deadline
    }
    return dict


def choose_new_tenders(current_response, old_numbers):
    # with open('index.html', 'w', encoding='utf-8') as file:
    #     file.write(current_response)

    soup = BeautifulSoup(current_response, 'lxml')
    all_tenders = soup.find_all('div', class_='row no-gutters registry-entry__form mr-0')
    results = []
    new_numbers = []
    for tender in all_tenders:
        number = tender.find('div', class_='registry-entry__header-mid__number').text.strip().split(' ')[1]
        new_numbers.append(number)

    intersection = set(new_numbers).intersection(old_numbers)

    for tender in all_tenders:
        number = tender.find('div', class_='registry-entry__header-mid__number').text.strip().split(' ')[1]
        if number not in intersection:
            tender_data = get_tender_data(tender)
            results.append(tender_data)

    # with open('results.json', 'w', encoding='utf-8') as file:
    #     json.dump(results, file, indent=4, ensure_ascii=False)

    return set(new_numbers), results


def get_data():
    sleep_time = 300
    last_response = ''
    old_numbers = set()

    # За итерацию:
    # если страница изменилась:
    #   1) собираем номера тендеров с первой странице
    #   2) сравниваем с номерами первой страницы при предыдущем запросе
    #   3) тендеры, номера которых не было при предыдущей итерации, отправляются на почту одним письмом
    # спим перед следующей итерацией

    while True:
        user_agent = UserAgent(os='linux').random
        url = 'https://zakupki.gov.ru/epz/order/extendedsearch/results.html'
        headers = {
            'User-Agent': user_agent,
            'Accept': '*/*'
        }

        current_response = requests.get(url=url, headers=headers).text
        if current_response != last_response:
            old_numbers, results = choose_new_tenders(current_response, old_numbers)
            send_email(results)

        last_response = current_response
        sleep(sleep_time)



def main():
    print('start request')
    res = requests.get('https://zakupki.gov.ru/epz/order/extendedsearch/results.html')
    print(res.status_code)
    print('end request')

    # get_data()


if __name__ == '__main__':
    main()
