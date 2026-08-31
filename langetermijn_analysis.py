import time
import os
import requests

from xml.etree import ElementTree as ET
from datetime import timedelta
from datetime import datetime
from matplotlib import cm
from matplotlib.dates import AutoDateFormatter, AutoDateLocator
import matplotlib.dates as mdates
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import locale
from datetime import datetime as dt
import sys

locale.setlocale(locale.LC_ALL, 'NL.utf8')
save = True

class OpenDataAPI:
    def __init__(self, api_token: str):
        self.base_url = "https://api.dataplatform.knmi.nl/open-data/v1"
        self.headers = {"Authorization": api_token}

    def __get_data(self, url, params=None):
        return requests.get(url, headers=self.headers, params=params).json()

    def list_files(self, dataset_name: str, dataset_version: str, params: dict):
        return self.__get_data(
            f"{self.base_url}/datasets/{dataset_name}/versions/{dataset_version}/files",
            params=params,
        )

    def get_file_url(self, dataset_name: str, dataset_version: str, file_name: str):
        return self.__get_data(
            f"{self.base_url}/datasets/{dataset_name}/versions/{dataset_version}/files/{file_name}/url"
        )

def download_file_from_temporary_download_url(download_url, filename, temploc):
    try:
        with requests.get(download_url, stream=True) as r:
            r.raise_for_status()
            floc = temploc + '/' + filename
            with open(floc, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
    except Exception:
        print('error')
        sys.exit(1)

    print(f"Successfully downloaded dataset file to {filename}")
    return floc

def plot_3d(x, y, z, labels, path,save=False):
    ax = plt.figure().add_subplot(projection='3d')

    ax.plot_trisurf(x, y, z, cmap=cm.coolwarm,
                           antialiased=True, linewidth=.0)

    ax.set_title(labels[0])
    ax.set_xlabel(labels[1])
    ax.set_ylabel(labels[2])
    ax.set_zlabel(labels[3])
    if(save):
        plt.savefig(path)
    plt.show()
    return

def plot_contour(x, y, zz, labels, path, ylim=None, colorlim=None,save=False):

    fig, ax = plt.subplots()
    w = max(x) // 10
    # w = (max(x)-x[0]).days/10
    h = max(y) // 6 * 2.5
    fig.set_size_inches(w, h)

    z = zz.copy()
    z[z > colorlim[1]] = colorlim[1]
    z[z < colorlim[0]] = colorlim[0]
    surf = ax.tricontourf(x, y, z, cmap=cm.coolwarm,
                          vmin=colorlim[0], vmax=colorlim[1], antialiased=True)

    ax.set_title(labels[0])
    ax.set_xlabel(labels[1])
    ax.set_ylabel(labels[2])

    # cbarticks = np.arange(colorlim[0], colorlim[1] + 1, sum([abs(cl) for cl in colorlim]) / 7)
    cbar = fig.colorbar(surf, ax=ax)
    cbar.set_label(labels[3])
    if(save):
        plt.savefig(path, bbox_inches="tight")
    plt.show()
    return

class timeit:
    def __init__(self):
        self._t = time.time()
        return

    def time(self):
        t = time.time()
        print(t - self._t)
        self._t = t
        return

    t=time

    def get(self):
        t = time.time()
        dt = (t - self._t)
        self._t = t
        return dt
    
def parse_KNMI_xml(floc):
    xml = ET.parse(floc)
    os.remove(floc)
    root = xml.getroot()

    vals = [[]] * 9
    tags = {'zonneschijnkans': 0, 'minimumtemp': 1,
            'maximumtemp': 2, 'windkracht': 3, 'dddd_dd_mmmm_yyyy': 4,
            'neerslagkans': 5, 'neerslaghoeveelheid_min': 6, 'neerslaghoeveelheid_max': 7, 'windrichting': 8,
            }

    for el in root[0]:
        i = [tags[tag] for tag in tags.keys() if tag in el.tag]
        if(i):
            i = i[0]
            vals[i] = vals[i] + [el.text]

    lens = [len(x) for x in vals]

    df = pd.DataFrame(vals).T
    df.columns = list(tags.keys())
    dmy = df.dddd_dd_mmmm_yyyy
    locale.setlocale(locale.LC_ALL, 'NL')
    d6 = datetime.strptime(' '.join(dmy[6].split()[1:]), '%d %B %Y')

    d7p = [datetime.strftime(d6 + timedelta(i), '%A %d %B %Y')
           for i in range(1, 8)]
    dmy[7:] = d7p[:len(dmy[7:])]
    df['dddd_dd_mmmm_yyyy'] = dmy

    return df

def get_data_knmi(saveloc, year=2023):
    t = timeit()
    # some data retrieval api stuff
    Rate = 1 / 200  # 200 per second
    cpi = 3
    Quota = 1000  # 1000 per hour
    y = str(year)
    # private
    api_key = ''
    # https://api.dataplatform.knmi.nl/open-data/v1/datasets/outlook_weather_forecast/versions/1.0/files

    api = OpenDataAPI(api_token=api_key)
    # api_url = "https://api.dataplatform.knmi.nl/open-data"
    # api_version = "v1"

    dataset_name = 'outlook_weather_forecast'
    dataset_version = '1.0'

    temploc = os.getcwd()
    monthdays = [(dt.strptime(f'{y}0101', '%Y%m%d') +  # did 2024 and 2023 now
                  timedelta(days=i)).strftime('%m-%d') for i in range(365)]
    if (monthdays[-1] != '12-31'):  # schrikkeljaar
        monthdays += ['12-31']

    d = t.get()
    total = 0

    # start the count!
    cdate = ''
    for date in monthdays:
        # 302 1510
        if(cdate and cdate != date):
            print('skipping ' + date)
            continue

        cdate = ''
        print(date)
        # add rate & quota

        # beter dan een request van 1000 keys voor 20 dagen..
        params = {"maxKeys": 5, "orderBy": "created", "sorting": "asc",
                  "begin": f"{y}-" + date + "T00:00:00+00:00", "end": f"{y}-12-31T23:59:59+00:00"}
        response = api.list_files(dataset_name, dataset_version, params)
        files = [f['filename']
                 for f in response['files'] if f['filename'].endswith('.xml')]
        first_file = files[0]
        mindate = files[0].split('.')[0].split('_')[-1]
        md = mindate[4:6] + '-' + mindate[6:8]
        if(date != md):
            cdate = md
        response = api.get_file_url(dataset_name, dataset_version, first_file)
        floc = download_file_from_temporary_download_url(
            response["temporaryDownloadUrl"], first_file, temploc)

        # check
        df = parse_KNMI_xml(floc)

        df.to_csv(saveloc, index=False, mode='a', header=False)

        total += cpi
        d = t.get()
        if (d <= Rate * cpi):
            time.sleep(Rate * cpi * 2)
        if (total > Quota - 100):
            print('hourly limit almost reached, stopping for now')
            # stop the count!
            break
    return


# plotjes full dataset
saveloc = os.getcwd()+"/knmi_longterm.csv"

# get_data_knmi(saveloc, year=2023)
# get_data_knmi(saveloc, year=2024)
saveloc2 = os.getcwd()+'/'
path=saveloc2

ys = [2023,2024]
df = pd.read_csv(saveloc)
for y in ys:
    df = pd.concat([df,pd.read_csv(saveloc2 + str(y) + '.csv')])

# %%
# fix some errors
# parsing errors, missing dates and incorrect numbers

# two different crawls mixed is not good!
#df = df[~df.windrichting.isna()]

df['groups'] = df.dmy.isna().diff().cumsum().fillna(0).astype(int)

first = df[df.groups == 0][-1 * len(df[df.groups == 1]):]
others = df.loc[((df.groups - 1) % 2) == 1]
others = others[others.groups > 1]
grplen = [len(df[df.groups == 1])] + \
    list(others.groupby('groups').size().values)

locale.setlocale(locale.LC_ALL, 'NL')
df.dmy = pd.to_datetime(df.dmy, format='%A %d %B %Y', errors='coerce')

if (grplen != [0]):
    for i, row in df.iterrows():
        if (row.groups != 0):  # start the fix
            if (row.groups % 2):
                shift = 1
                row.dmy = datetime.strftime(datetime.strptime(
                    df.loc[i - shift].dmy, '%A %d %B %Y') + timedelta(days=shift), '%A %d %B %Y')
            else:
                shift = grplen[int(np.floor(row.groups / 2)) - 1] * 2
                row.dmy = datetime.strftime(datetime.strptime(
                    df.loc[i - shift].dmy, '%A %d %B %Y') + timedelta(days=1), '%A %d %B %Y')

            df.loc[i] = row

    df = df.drop('groups', axis=1)

# remove other parsing errors such as &nbsp
df = df.drop('groups', axis=1)
for c in df.columns[:-1]:
    df[c] = pd.to_numeric(df[c], errors='coerce')

# df.to_csv(saveloc, index=False)

# %%
# check accuracy of the predictions, last prediction is taken as true value (yeah.. but whatever)
# soort van handmatige pluim

# last (true?) val
last = df.drop_duplicates(subset='dmy', keep='last')

# all
# get diff
# get +- where 95% is in this range

# drop windrichting for now
df = df.drop('windrichting',axis=1)

dfd = df[df.duplicated(subset='dmy', keep='last')] - df.groupby(
    'dmy').transform('last')[df.duplicated(subset='dmy', keep='last')]
dfd['dmy'] = df[df.duplicated(subset='dmy', keep='last')].dmy

dfd = dfd[dfd.duplicated(subset='dmy')]
dfd['cnt'] = dfd.groupby('dmy').transform(
    'size') - dfd.groupby('dmy').cumcount()

dfd = dfd.reset_index(drop=True)
dfd = dfd.sort_values('dmy')
#dfd.dmy = pd.to_datetime(df.dmy, format='%A %d %B %Y')
dfd.dmy = pd.to_datetime(dfd.dmy)  # , format='%A %d %B %Y')
dfd = dfd[dfd.dmy <= dt.now()]

# show plume per day-ahead
dfd2 = dfd.drop('dmy', axis=1)
sm = np.unique(dfd.cnt, return_counts=True)[1]
mean = dfd2.groupby('cnt').mean()
meanabs = dfd2.abs().groupby('cnt').mean()
sd = dfd2.groupby('cnt').std()
lower5 = mean - sd * 2
upper95 = mean + sd * 2

for c in sd.columns:
    fig, ax = plt.subplots(1, 1)
    ax.set_xlabel('days ahead of day1 prediction')
    ax.set_ylabel(c)
    ax.set_title('pluim ' + c + ' day2+ compared to day_ahead prediction')
    ax.plot(lower5[c], label='lower5')
    ax.plot(mean[c], label='mean deviation')
    ax.plot(upper95[c], label='upper95')
    ax.plot(meanabs[c], label='abs mean deviation')

    plt.subplots_adjust(bottom=.2, top=.9)

    plt.legend(reverse=True)

    fig.tight_layout()
    ax.grid('y')
    if(save):
        plt.savefig(path + 'pluim ' + c + ' mean.svg')
    plt.show()

df3 = dfd.reset_index(drop=True).copy()
df3.dmy = df3.dmy.dt.tz_localize('UTC')

for c in df3.columns[1:-1]:
    z = df3[c].dropna()
    x = (df3.dmy - df3.dmy[0]).apply(lambda x: x.days)[z.index].values
    y = df3.cnt[z.index].values
    z = z.values

    ylim = [-2 * sd.max()[c], 2 * sd.max()[c]]
    cl = ylim

    title = c + ' diff of prediction compared to day_ahead prediction'
    xlabel = 'date'
    ylabel = 'days_prediction_ahead'
    zlabel = c + '\nerror, cutoff +-2σ: ' + str(np.round(cl[1], 2))
    p = path + 'errors per day ' + c + '.svg'

    # plot_3d(x,y,z,[title,xlabel,ylabel,zlabel],p)
    plot_contour(x, y, z, [title, xlabel, ylabel, zlabel], p, ylim, cl,save)
