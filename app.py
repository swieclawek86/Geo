import csv
import io
import json
from datetime import date, timedelta
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from streamlit_calendar import calendar as schedule_calendar
from engine import load_database, allocate, schedule

st.set_page_config(page_title='Development Program Planner',page_icon='📈',layout='wide')
st.title('Development Program Planner')
st.caption('Well inventory · Onstream scheduling · Production wedges · Capital forecasts')
st.warning('PUBLIC DEMO — synthetic well data only. Do not upload or enter proprietary company information.')

@st.cache_data(show_spinner=False)
def parse_book(data):
    return load_database(data)

source=(Path(__file__).parent/'sample_well_database.xlsx').read_bytes()
with st.sidebar:
    st.header('Demo database')
    st.success('Synthetic well forecasts loaded automatically')
    st.caption('For public demonstration, workbook uploads are disabled.')

try:
    wells, forecasts=parse_book(source)
    original=sorted({str(w.get('Formation','')) for w in wells})
    formation_names={name:f'Formation {i+1}' for i,name in enumerate(original)}
    for w in wells:w['Formation']=formation_names[str(w.get('Formation',''))]
except Exception as e:
    st.error(f'Unable to import workbook: {e}');st.stop()
import hashlib
fingerprint=hashlib.sha256(source).hexdigest()
if st.session_state.get('dataset')!=fingerprint:
    st.session_state['dataset']=fingerprint
    st.session_state['dates']={w['Well_ID']:w['online'] for w in wells}

with st.sidebar:
    st.divider();st.header('2027 program window')
    start=st.date_input('Year start',date(2027,1,4))
    break_start=st.date_input('Mid-season break starts',date(2027,4,1))
    break_end=st.date_input('Mid-season break ends',date(2027,6,30))
    end=st.date_input('Year end',date(2027,12,31))
    gap=st.number_input('Days between well onstream dates',min_value=1,max_value=365,value=21)
    horizon=st.number_input('Production forecast through',min_value=2026,max_value=2060,value=2032)
    st.caption('The break dates are inclusive; capital is assigned to onstream month in this prototype.')

for w in wells:w['online']=st.session_state['dates'].get(w['Well_ID'])
forms=sorted({str(w.get('Formation','')) for w in wells})
filt=st.multiselect('Filter wells by formation',forms,default=forms)
visible=[w for w in wells if str(w.get('Formation','')) in filt]
sel=st.multiselect('Wells to auto-schedule',[w['Well_ID'] for w in visible],default=[w['Well_ID'] for w in visible if w['online'] is None])
a,b,c=st.columns([1,1,2])
with a:
    if st.button('Schedule selected',type='primary',use_container_width=True):
        try:
            n=schedule(wells,set(sel),start,break_start,break_end,end,int(gap))
            st.session_state['dates']={w['Well_ID']:w['online'] for w in wells}
            st.rerun()
            st.success(f'Scheduled {n} wells; {len(sel)-n} did not fit the window.')
        except Exception as e:st.error(str(e))
with b:
    if st.button('Clear selected dates',use_container_width=True):
        for wid in sel:st.session_state['dates'][wid]=None
        st.rerun()
with c:
    st.caption('Move existing well bars on the Gantt chart, or use the exact-date editor below.')

st.subheader('Drag-and-drop development schedule')
st.caption('Drag a well horizontally to change its onstream date. Each row is an entity. The grey break is unavailable; moves outside the program dates are rejected. Dragging does not change well duration or forecast curve.')
valid_window = start <= break_start <= break_end <= end
if not valid_window:
    st.error('Dates must satisfy year start ≤ break start ≤ break end ≤ year end.')

def allowed(d):
    return start <= d <= end and not break_start <= d <= break_end

colors=['#2563eb','#0d9488','#b45309','#9333ea','#be123c','#4f46e5']
color_by_form={f:colors[i%len(colors)] for i,f in enumerate(forms)}
resources=[{'id':w['Well_ID'],'title':f"{w['Well_ID']} · {w['Formation']}"} for w in visible]
events=[]
for w in visible:
    dt=st.session_state['dates'].get(w['Well_ID'])
    if dt:
        events.append({'id':w['Well_ID'],'resourceId':w['Well_ID'],'title':w['Well_ID'],
            'start':dt.isoformat(),'end':(dt+timedelta(days=7)).isoformat(),
            'backgroundColor':color_by_form[w['Formation']],'borderColor':color_by_form[w['Formation']],
            'editable':True,'durationEditable':False,'resourceEditable':False})
# Render the non-operating period on every visible resource row.
for w in visible:
    events.append({'id':'break_'+w['Well_ID'],'resourceId':w['Well_ID'],
         'start':break_start.isoformat(),'end':(break_end+timedelta(days=1)).isoformat(),
         'display':'background','backgroundColor':'#cbd5e1','editable':False})
if valid_window:
    options={'initialView':'resourceTimelineMonth', 'schedulerLicenseKey':'GPL-My-Project-Is-Open-Source',
         'resources':resources,'resourceAreaHeaderContent':'Well entity · Formation',
         'resourceAreaWidth':'31%', 'editable':True,'eventStartEditable':True,'eventDurationEditable':False,
         'eventResourceEditable':False,'height':max(420,110+len(visible)*42),
         'slotMinWidth':30,'slotDuration':{'days':1},'eventOverlap':True,
         'initialDate':start.isoformat(),
         'headerToolbar':{'left':'prev,next today','center':'title','right':'resourceTimelineMonth,resourceTimelineWeek'},
         'views':{'resourceTimelineMonth':{'type':'resourceTimeline','duration':{'months':1}},
                  'resourceTimelineWeek':{'type':'resourceTimeline','duration':{'weeks':1}}}}
    change=schedule_calendar(events=events, options=options, callbacks=['eventChange'],key='well_gantt',
        custom_css='.fc-datagrid-cell-main {font-size: 12px;} .fc-event-title {font-weight: 600;}')
    if change and change.get('callback')=='eventChange':
        ev=change.get('eventChange',{}).get('event',{})
        wid=str(ev.get('id',''))
        if wid in st.session_state['dates']:
            try:
                moved=date.fromisoformat(ev['start'][:10])
                if allowed(moved):
                    if st.session_state['dates'][wid]!=moved:
                        st.session_state['dates'][wid]=moved
                        st.rerun()
                else:
                    st.warning(f'{wid}: {moved} is outside the allowable drilling season. Move was not saved.')
                    st.rerun()
            except (KeyError,ValueError,TypeError):
                st.warning('Could not read the new event date.')
else:
    st.info('Correct the program window to enable drag-and-drop scheduling.')

with st.expander('Edit exact well dates / schedule unscheduled wells'):
    frame=pd.DataFrame([{'Well_ID':w['Well_ID'],'Formation':w['Formation'],
        'Onstream_Date':st.session_state['dates'].get(w['Well_ID']),
        'Capital_CAD_Gross':w['Capital_CAD'],'Working_Interest':w['WI']} for w in visible])
    frame['Onstream_Date']=pd.to_datetime(frame['Onstream_Date'])
    edited=st.data_editor(frame,use_container_width=True,hide_index=True,key='date_editor',
        column_config={'Onstream_Date':st.column_config.DateColumn('Onstream',format='YYYY-MM-DD')},
        disabled=['Well_ID','Formation','Capital_CAD_Gross','Working_Interest'],num_rows='fixed')
    if st.button('Apply edited dates'):
        updates={}
        for _,r in edited.iterrows():
            dt=None if pd.isna(r['Onstream_Date']) else pd.Timestamp(r['Onstream_Date']).date()
            if dt and not allowed(dt):
                st.error(f"{r['Well_ID']}: invalid date {dt}")
                st.stop()
            updates[r['Well_ID']]=dt
        st.session_state['dates'].update(updates)
        st.rerun()

for w in wells:w['online']=st.session_state['dates'][w['Well_ID']]
monthly,well_totals=allocate(wells,forecasts,int(horizon))
months=sorted(monthly)
annual={}
for dt,info in monthly.items():
    a=annual.setdefault(dt.year,{'Year':dt.year,'Oil_bbl':0.,'Gas_Mcf':0.,'Capital_CAD':0.})
    for metric in ('Oil_bbl','Gas_Mcf','Capital_CAD'):a[metric]+=info[metric]
annual_df=pd.DataFrame([annual[y] for y in sorted(annual)])
if annual_df.empty:annual_df=pd.DataFrame(columns=['Year','Oil_bbl','Gas_Mcf','Capital_CAD'])
cols=st.columns(4)
cols[0].metric('Scheduled wells',sum(w['online'] is not None for w in wells))
cols[1].metric('Net development capital',f"${sum(x['Capital_CAD'] for x in well_totals.values())/1e6:,.1f} MM")
cols[2].metric('Forecast oil',f"{sum(x['Oil_bbl'] for x in well_totals.values())/1e3:,.0f} Mbbl")
cols[3].metric('Forecast gas',f"{sum(x['Gas_Mcf'] for x in well_totals.values())/1e6:,.2f} Bcf")

st.subheader('Production wedge')
metric=st.selectbox('Display', ['Oil (bbl/d)','Gas (Mcf/d)','Oil (Mbbl/month)','Gas (MMcf/month)'])
mode='Oil' if metric.startswith('Oil') else 'Gas'
fig=go.Figure()
vintages=sorted({key.split('_',1)[1] for d in monthly.values() for key in d if key.startswith(mode+'_')})
for vint in vintages:
    vals=[]
    for month in months:
        value=monthly[month].get(mode+'_'+vint,0)
        if metric.endswith('/d'):
            import calendar
            value/=calendar.monthrange(month.year,month.month)[1]
        elif metric.startswith('Oil'):value/=1000
        else:value/=1e6
        vals.append(value)
    fig.add_trace(go.Scatter(x=months,y=vals,stackgroup='production',name=vint,mode='lines',line={'width':0.5}))
fig.update_layout(height=410,xaxis_title='Calendar month',yaxis_title=metric,legend_title='Onstream year',margin=dict(l=20,r=20,t=20,b=20),hovermode='x unified')
st.plotly_chart(fig,use_container_width=True)

st.subheader('Capital schedule')
capital_fig=go.Figure(go.Bar(x=[r['Year'] for _,r in annual_df.iterrows()],y=[r['Capital_CAD']/1e6 for _,r in annual_df.iterrows()]))
capital_fig.update_layout(height=260,xaxis_title='Year',yaxis_title='Net capital (CAD MM)',margin=dict(l=20,r=20,t=20,b=20))
st.plotly_chart(capital_fig,use_container_width=True)
st.subheader('Annual summary')
st.dataframe(annual_df,use_container_width=True,hide_index=True)
monthly_rows=[{'Month':dt.isoformat(),'Oil_bbl':v['Oil_bbl'],'Gas_Mcf':v['Gas_Mcf'],'Capital_CAD':v['Capital_CAD']} for dt,v in sorted(monthly.items())]
well_rows=[{'Well_ID':w['Well_ID'],'Formation':w.get('Formation',''),'Onstream_Date':w['online'].isoformat() if w['online'] else '', 'Capital_CAD':well_totals[w['Well_ID']]['Capital_CAD'],'Oil_bbl':well_totals[w['Well_ID']]['Oil_bbl'],'Gas_Mcf':well_totals[w['Well_ID']]['Gas_Mcf']} for w in wells]

def csv_bytes(rows,columns):
    io_string=io.StringIO();writer=csv.DictWriter(io_string,fieldnames=columns);writer.writeheader();writer.writerows(rows)
    return io_string.getvalue().encode('utf-8-sig')

st.subheader('Exports')
x,y,z=st.columns(3)
with x:st.download_button('Annual CSV',csv_bytes(annual_df.to_dict('records'),['Year','Oil_bbl','Gas_Mcf','Capital_CAD']),'annual_summary.csv','text/csv',use_container_width=True)
with y:st.download_button('Monthly CSV',csv_bytes(monthly_rows,['Month','Oil_bbl','Gas_Mcf','Capital_CAD']),'monthly_profile.csv','text/csv',use_container_width=True)
with z:st.download_button('Well schedule CSV',csv_bytes(well_rows,['Well_ID','Formation','Onstream_Date','Capital_CAD','Oil_bbl','Gas_Mcf']),'well_schedule.csv','text/csv',use_container_width=True)
scenario={'source_sha256':fingerprint,'dates':{k:v.isoformat() if v else None for k,v in st.session_state['dates'].items()}}
st.download_button('Save scenario (JSON)',json.dumps(scenario,indent=2),'scenario.json','application/json')
loaded=st.file_uploader('Load previously saved scenario',type='json')
if loaded and st.button('Apply scenario'):
    try:
        data=json.loads(loaded.getvalue())
        if data['source_sha256']!=fingerprint:raise ValueError('This scenario was saved against a different Excel workbook.')
        st.session_state['dates']={w['Well_ID']:date.fromisoformat(data['dates'][w['Well_ID']]) if data['dates'].get(w['Well_ID']) else None for w in wells}
        st.rerun()
    except Exception as exc:st.error(f'Cannot load scenario: {exc}')
st.caption('Prototype limitations: schedule spacing is not a rig model; costs occur in the onstream month; forecasts are gross monthly oil bbl and gas Mcf, WI-netted. No shared scenario store, background jobs or authentication is included.')
