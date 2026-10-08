"""Dependency-light parsing and aggregation for gross forecast volumes and WI-net results."""
import calendar
import io
import zipfile
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import date, timedelta

NS = {'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main','r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}

def xlsx_tables(blob):
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        strings=[]
        if 'xl/sharedStrings.xml' in z.namelist():
            root=ET.fromstring(z.read('xl/sharedStrings.xml'))
            for si in root.findall('m:si',NS):
                strings.append(''.join(n.text or '' for n in si.findall('.//m:t',NS)))
        book=ET.fromstring(z.read('xl/workbook.xml'))
        rels=ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
        targets={r.get('Id'):r.get('Target') for r in rels}
        result={}
        for sh in book.findall('m:sheets/m:sheet',NS):
            target=targets[sh.get('{%s}id'%NS['r'])].lstrip('/')
            part=target if target.startswith('xl/') else 'xl/'+target
            root=ET.fromstring(z.read(part)); rows=[]
            for row in root.findall('m:sheetData/m:row',NS):
                cells={}
                for c in row.findall('m:c',NS):
                    ref=c.get('r','A1'); col=0
                    for char in ref:
                        if not char.isalpha():break
                        col=col*26+ord(char.upper())-64
                    v=c.find('m:v',NS); inline=c.find('m:is',NS); typ=c.get('t')
                    value=v.text if v is not None else ''
                    if typ=='s' and value:value=strings[int(value)]
                    elif typ=='inlineStr' and inline is not None:value=''.join(n.text or '' for n in inline.findall('.//m:t',NS))
                    elif typ not in ('str','e') and value:
                        try:value=float(value)
                        except ValueError:pass
                    cells[col-1]=value
                if cells:
                    values=['']*(max(cells)+1)
                    for col,value in cells.items(): values[col]=value
                    rows.append(values)
            if rows:
                headers=[str(x).strip() for x in rows[0]]
                result[sh.get('name')]=[dict(zip(headers,row+['']*(len(headers)-len(row)))) for row in rows[1:]]
        return result

def as_date(v):
    if isinstance(v,date):return v
    if isinstance(v,(float,int)):return date(1899,12,30)+timedelta(days=int(v))
    return date.fromisoformat(str(v).strip()[:10])

def num(v,default=0.):
    return float(v) if v not in ('',None) else default

def next_month(d,n):
    y=d.year+(d.month-1+n)//12; m=(d.month-1+n)%12+1
    return date(y,m,min(d.day,calendar.monthrange(y,m)[1]))

def load_database(blob):
    sheets=xlsx_tables(blob)
    if not {'Wells','Forecasts'}.issubset(sheets):raise ValueError('Workbook requires Wells and Forecasts sheets.')
    wells=sheets['Wells']; forecast=defaultdict(dict)
    if not wells:raise ValueError('Wells sheet is empty.')
    for col in ('Well_ID','Capital_CAD','Working_Interest'):
        if col not in wells[0]:raise ValueError('Missing Wells column: '+col)
    for line in sheets['Forecasts']:
        wid=str(line.get('Well_ID','')).strip(); ix=int(num(line.get('Month_Index')))
        if wid and ix>=1:
            if ix-1 in forecast[wid]:raise ValueError('Duplicate forecast month for '+wid)
            forecast[wid][ix-1]=(num(line.get('Oil_bbl')),num(line.get('Gas_Mcf')))
    ids=[]
    for w in wells:
        w['Well_ID']=str(w.get('Well_ID','')).strip(); wid=w['Well_ID'];ids.append(wid)
        if not wid:raise ValueError('Blank Well_ID.')
        w['Capital_CAD']=num(w.get('Capital_CAD'))
        wi=num(w.get('Working_Interest'),1)
        if wi>1:wi/=100.
        if not 0<=wi<=1:raise ValueError('Working Interest must be 0–1 or 0–100 for '+wid)
        w['WI']=wi
        raw=w.get('Onstream_Date')
        w['online']=as_date(raw) if raw not in ('',None) else None
        if not forecast.get(wid):raise ValueError('Missing forecast for '+wid)
        if sorted(forecast[wid])!=list(range(len(forecast[wid]))):raise ValueError('Nonconsecutive forecast months for '+wid)
    if len(ids)!=len(set(ids)):raise ValueError('Duplicate Well_ID values.')
    return wells,dict(forecast)

def allocate(wells, forecasts, end_year):
    """Allocate vintage monthly profiles across calendar months by overlap-days."""
    monthly=defaultdict(lambda:defaultdict(float))
    by_well=defaultdict(lambda:defaultdict(float))
    cutoff=date(end_year+1,1,1)
    for w in wells:
        online=w.get('online')
        if not online:continue
        wid=w['Well_ID'];wi=w['WI'];vintage=str(online.year)
        capital=w['Capital_CAD']*wi
        if online<cutoff:
            month=date(online.year,online.month,1)
            monthly[month]['Capital_CAD']+=capital
            by_well[wid]['Capital_CAD']+=capital
        for age,(oil,gas) in forecasts[wid].items():
            start=next_month(online,age); end=next_month(online,age+1)
            if start>=cutoff:break
            days=(end-start).days
            position=start
            while position<min(end,cutoff):
                mdate=date(position.year,position.month,1)
                nextcal=next_month(mdate,1)
                part_end=min(nextcal,end,cutoff)
                f=(part_end-position).days/days*wi
                ov=oil*f;gv=gas*f
                monthly[mdate]['Oil_bbl']+=ov;monthly[mdate]['Gas_Mcf']+=gv
                monthly[mdate]['Oil_'+vintage]+=ov;monthly[mdate]['Gas_'+vintage]+=gv
                by_well[wid]['Oil_bbl']+=ov;by_well[wid]['Gas_Mcf']+=gv
                position=part_end
    return monthly,by_well

def schedule(wells,selected,start,break_start,break_end,end,gap):
    if not start<=break_start<=break_end<=end:raise ValueError('Require start ≤ break start ≤ break end ≤ year end.')
    if gap<1:raise ValueError('Spacing must be at least one day.')
    cursor=start; count=0
    for w in wells:
        if w['Well_ID'] not in selected:continue
        if break_start<=cursor<=break_end:cursor=break_end+timedelta(days=1)
        if cursor>end:break
        w['online']=cursor;count+=1;cursor+=timedelta(days=gap)
    return count
