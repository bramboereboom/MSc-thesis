import pandas as pd


# https://ev-database.nl/cheatsheet/accu-capaciteit-elektrische-auto
df = pd.read_html('ev-power.html')
df = df[0]
df.columns = ['model', 'kwh']
df['clean'] = df['kwh'].str.strip('Gemiddelde')
df['clean'] = df['clean'].str.strip('Kwh')
df['clean'] = df['clean'].str.strip('kW')
df['clean'] = df['clean'].str.strip(' ')
df['clean'] = df['clean'].str.replace(',', '.')
df['clean'] = df['clean'].astype(float)
df['clean'].hist()