import streamlit as st
import random
import pandas as pd
from gsheetsdb import connect
import requests
from bs4 import BeautifulSoup



# --- Read historical data from google sheet --------
@st.cache(ttl=600, allow_output_mutation=True)
def run_query(query):
    # Create a connection object
    conn = connect()

    rows = conn.execute(query, headers=1)
    rows = rows.fetchall()
    return rows

sheet_url = st.secrets["source1_url"]
rows = run_query(f'SELECT * FROM "{sheet_url}"')
df = pd.DataFrame(data=rows, columns=['Date', 'num1', 'num2', 'num3', 'num4', 'num5', 'num6', 'bonus'])

# set the data types
df.num1 = pd.to_numeric(df.num1, downcast='integer')
df.Date = pd.to_datetime(df.Date)
df[['num1', 'num2', 'num3', 'num4', 'num5', 'num6', 'bonus']] = \
   df[['num1', 'num2', 'num3', 'num4', 'num5', 'num6', 'bonus']].astype('int8')


# --- Get current data from web -------------
@st.cache(ttl=600)
def get_current_results(thelink):
    url = thelink
    r = requests.get(url)
    r.encoding = 'utf-8'
    if r.status_code == requests.codes.ok:
        data = BeautifulSoup(r.text, 'html.parser')
        theArea = data.select('div.col.s_8_12 > *')
        rows = []
        for theRow in theArea:    
            #print(theRow.contents[0].contents[0])
            arr = [theRow.contents[0].contents[0]]

            for sect in theRow:
                wb = sect.select('span.white') # the 6 numbers
                for w in wb:
                    #print(w.text)
                    arr.append(w.text)
                    
                gb = sect.select('.grey')
                for g in gb:
                    #print(g.contents[0])
                    arr.append(g.contents[0])

            rows.append(arr)

    # convert data to dataframe
    dd = pd.DataFrame(data=rows, columns=['Date','num1','num2','num3', 'num4', 'num5', 'num6', 'bonus'] )
    dd.Date = pd.to_datetime(dd.Date, infer_datetime_format=True)
    dd.iloc[:,1:8] = dd.iloc[:,1:8].astype('int8')
    return dd

weblink = st.secrets["source2_url"]
dd = get_current_results(weblink)




# ----- merge history and current data -----
dd = dd[(dd.Date > df.Date.max())]
df = pd.concat([dd.sort_values(by='Date', ascending=False), df])
df['NumList'] = df.iloc[:,1:7].values.tolist()



# --------begin streamlit interface-----------------
# initialize state
if 'num' not in st.session_state:
    st.session_state['num'] = 4

randnums = random.sample(range(1, 50), 6)
randnums.sort()
for x in range(0, 6):
    if f'n{x}' not in st.session_state:
        st.session_state[f'n{x}'] = randnums[x]


st.write("Inspired by the creator of Wordle, I created this tool for my wife to check her Ontario49 numbers. ;)")

num = st.number_input('Enter minimumm desired matches [.5 for bonus number]:', 3., 6., step=0.5, \
                      format='%f', key='num')

st.write('Enter your chosen numbers:')
cols = st.columns(6)
num1 = cols[0].number_input('', 1, 49, key='n0')
num2 = cols[1].number_input('', 1, 49, key='n1')
num3 = cols[2].number_input('', 1, 49, key='n2')
num4 = cols[3].number_input('', 1, 49, key='n3')
num5 = cols[4].number_input('', 1, 49, key='n4')
num6 = cols[5].number_input('', 1, 49, key='n5')

if st.button('Submit'):
    nums = [num1, num2, num3, num4, num5, num6]
    if len(set(nums)) < 6:
        st.warning('Cannot have repeated numbers')
    else:
        # compute matches based on user's numbers
        df['Matches'] = (df.NumList.iloc[:].apply(lambda x: len(set(x).intersection(set(nums))))
                 + df.bonus.iloc[:].apply(lambda x: int(x in set(nums)) * 0.5))    
        
        # Proceed to show results
        # CSS to inject contained in a string
        hide_dataframe_row_index = """
                    <style>
                    .row_heading.level0 {display:none}
                    .blank {display:none}
                    .col_heading   {text-align: center !important}
                    </style>
                    """
        # Inject CSS with Markdown
        st.markdown(hide_dataframe_row_index, unsafe_allow_html=True)
        # filter the results to user's desired number of matches and display it
        fmt = "%Y-%m-%d"
        st.table(df[df.Matches >= num][['Date', 'num1', 'num2', 'num3','num4', 'num5', 'num6', 'bonus', 'Matches']] \
                 .style.format({ "Date": lambda t: t.strftime(fmt), "Matches":"{:.1f}"}))
else:
    st.write('')
