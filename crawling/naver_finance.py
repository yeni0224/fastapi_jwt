import pandas as pd
import requests
from bs4 import BeautifulSoup

#[ CODE 1 ]
#네이버 금융 국내 증시 상위 100의 기업 이름과 url 크롤링
def get_top100(top100_url, top100_name):
    url = 'https://finance.naver.com/sise/sise_quant.nhn'
    result = requests.get(url)
    html = BeautifulSoup(result.content, 'html.parser')
    top100 = html.find_all('a', {'class':'tltle'})

    for i in range(100):
        url = 'https://finance.naver.com'+top100[i]['href']
        top100_url.append(url)

        company_name = top100[i].string
        top100_name.append(company_name)
    return top100_url, top100_name

#[ CODE 2 ] 검색할 기업 입력받기
def get_company(top100_name):
    company_name = input("주가를 검색할 기업 이름을 입력하세요:")

    for i in range(100):
        if company_name ==top100_name[i]:
            return i
    if i == 100:
        print("입력한 기업은 상위100 목록에 없습니다.")
        return(100)    
    
#[ CODE 3 ] company_url에 대한 기업 주식 정보 페이지 크롤링
def get_company_stockPage(company_url):
    result = requests.get(company_url)
    company_stockPage = BeautifulSoup(result.content, 'html.parser')
    return company_stockPage

#[ CODE 4 ] 기업의 현재 주가 데이터 크롤링
def get_price(company_url):
    company_stockPage= get_company_stockPage(company_url) #[CODE 3]
    no_today = company_stockPage.find('p',{'class':'no_today'})
    blind = no_today.find('span',{'class':'no_today'})
    now_price = blind.text
    return now_price

#[ CODE 0 ]
def main():
    top100_url = []
    top100_name = []

    top100_url, top100_name = get_top100(top100_url, top100_name)

    print("< 현재 네이버 금융 국내 코스피 상위100 기업 목록 >")
    print(top100_name)
    print('')

    company = int(get_company(top100_name)) # [CODE 2]
    if company == 100:
        print('상위 100 목록에 존재하지 않는 기업입니다')
    else:
        now_price = get_price(top100_url[company]) # [CODE 4]
        print('%s 기업의 현재 주가는 %s 입니다' % (top100_name[company], now_price))

if __name__ == '__main__':
    main()