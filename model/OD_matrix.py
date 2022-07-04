import pandas as pd


def generate_OD(g, m):
    OD = pd.read_csv("../data/afstand7.csv", sep=";")
    gemeenten = pd.read_csv('../data/gemeenten.csv')

    OD = pd.merge(how='left', left=OD, right=gemeenten, left_on='origin_id', right_on='GM_CODE')
    OD = OD[['origin_id', 'destination_id', 'GM_NAAM', 'total_cost', 'AANT_INW']]
    OD = OD.rename(columns={'GM_NAAM':'origin', 'AANT_INW': 'INW_origin'})
    OD = pd.merge(how='left', left=OD, right=gemeenten, left_on='destination_id', right_on='GM_CODE')
    OD = OD.rename(columns={'GM_NAAM':'destination', 'AANT_INW':'INW_destination'})
    OD = OD[['origin_id', 'destination_id', 'origin','destination', 'total_cost','INW_origin','INW_destination']]
    # Computed distances used rijksdriehoekscoordinates, so distances in meters
    # Will be converted to KM.
    OD['distance'] = OD['total_cost'].fillna(0).apply(lambda x: x/1000)
    OD[['origin_id','destination_id','origin','destination','distance','INW_origin','INW_destination']]


    OD['flow'] = OD.apply(lambda row: g * ((row['INW_origin'] * row['INW_destination']) / (row['distance']**m) if row['distance'] != 0 else 0), axis=1)
    #OD = OD.pivot(index='origin_id', columns='destination_id', values='distance')
    OD['sum_flow'] = OD.groupby('origin')['flow'].transform('sum')
    OD['p_flow'] = OD['flow'] / OD['sum_flow'] * 100
    OD = dict(tuple(OD[['origin_id','destination_id','p_flow', 'distance']].groupby('origin_id')))
    for key, index in OD.items():
        index.drop('origin_id', axis=1, inplace=True)
    return OD


