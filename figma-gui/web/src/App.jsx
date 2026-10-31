import React, {useEffect, useState} from 'react';
import {Activity, ArrowUpRight, Battery, Check, ChevronRight, Database, Gauge, History, LockKeyhole, LogOut, Radio, Settings2, ShieldCheck, Thermometer, Wrench, Zap, Play, Pause, RefreshCw, Download, AlertTriangle} from 'lucide-react';
import {ResponsiveContainer, LineChart, Line, CartesianGrid, XAxis, YAxis, Tooltip, ReferenceLine} from 'recharts';

async function request(path, options = {}, csrf) {
  let response;
  try {
    response = await fetch('/api' + path, {...options, credentials:'same-origin', headers:{'Content-Type':'application/json', 'X-Requested-With':'VoltesseGUI', ...(csrf ? {'X-CSRF-Token':csrf}:{}), ...options.headers}});
  } catch { throw new Error('Cannot reach the backend. Check that the API is running.'); }
  let result;
  try { result = await response.json(); } catch { throw new Error('The API did not return JSON. Check the backend and Vite proxy configuration.'); }
  if (!response.ok) { const err = new Error(typeof result.detail === 'string' ? result.detail : 'Please check your input.'); err.status = response.status; throw err; }
  return result;
}
function useResource(key, load, interval = 0) {
  const [state,setState] = useState({});
  useEffect(()=>{
    let active=true, timer;
    async function refresh(){
      try { const data=await load(); if(active) setState({key,data}); }
      catch(error){if(active) setState({key,error});}
      if(active && interval) timer=setTimeout(refresh,interval);
    }
    refresh(); return ()=>{active=false;clearTimeout(timer);};
  },[key,interval]);
  return state.key === key ? state : {};
}
function Brand(){return <div className="brand"><div className="brand-symbol"><Zap size={24} fill="currentColor"/></div><div>VOLTESSE<span>DASH / TECHNICIAN</span></div></div>;}
function ErrorBox({error}){return <div role="alert" className="notice danger"><AlertTriangle size={17}/>{error.message || error}</div>;}
function Loading(){return <div className="empty"><RefreshCw size={20} className="spin"/> Loading data…</div>;}
function fmt(value, digits=1){return value == null ? '—' : Number(value).toLocaleString(undefined,{maximumFractionDigits:digits});}
function date(value){return new Date(value).toLocaleString(undefined,{dateStyle:'medium',timeStyle:'short'});}
function duration(seconds){return `${Math.floor(Number(seconds)/60)}:${String(Math.floor(Number(seconds)%60)).padStart(2,'0')}`;}
function Plot({title,subtitle,data,color='#c88721',limit,height=215}){
  return <section className="panel plot"><div className="panel-heading"><div><h3>{title}</h3><p>{subtitle}</p></div><Activity size={17}/></div>
    {!data?.length ? <div className="empty">No readings available for this chart.</div> : <div style={{height}}><ResponsiveContainer width="100%" height="100%"><LineChart data={data} margin={{top:15,right:25,bottom:5,left:0}}>
      <CartesianGrid strokeDasharray="3 4" vertical={false} stroke="#e9edef"/><XAxis dataKey="x" type="number" domain={['dataMin','dataMax']} tick={{fontSize:11}} tickFormatter={v=>fmt(v,1)} tickLine={false} axisLine={false}/><YAxis domain={limit != null ? [0, max=>Math.max(max+5,limit+5)] : ['auto','auto']} tick={{fontSize:11}} tickLine={false} axisLine={false} width={48}/><Tooltip formatter={v=>fmt(v,2)} labelFormatter={v=>fmt(v,2)}/>
      {limit != null && <ReferenceLine y={limit} stroke="#bd4c3f" strokeDasharray="5 4" label={{value:'Warning limit',position:'insideTopRight',fontSize:10,fill:'#bd4c3f'}}/>}
      <Line name={title} type="monotone" dataKey="y" stroke={color} strokeWidth={2.5} dot={data.length<25 ? {r:2}:false} isAnimationActive={false} connectNulls={false}/>
    </LineChart></ResponsiveContainer></div>}
  </section>;
}
function Login({onLogin,initialError}){
  const [username,setUsername]=useState(''),[password,setPassword]=useState(''),[busy,setBusy]=useState(false),[error,setError]=useState(initialError);
  async function submit(e){e.preventDefault();setBusy(true);setError(null);try{const user=await request('/auth/login',{method:'POST',body:JSON.stringify({username,password})});setPassword('');onLogin(user);}catch(e){setError(e);}finally{setBusy(false);}}
  return <div className="login-layout"><section className="login-story"><Brand/><div className="story-main"><span className="eyebrow">VOLTESSE FORMULA ELECTRIC</span><h1>Every reading.<br/>A clearer picture.</h1><p>Your workspace for vehicle telemetry, performance analysis, and trackside diagnostics.</p><div className="story-grid"><div><Activity/>LIVE TELEMETRY</div><div><History/>SESSION ANALYSIS</div><div><ShieldCheck/>PROTECTED ACCESS</div></div></div><p className="story-footer">ENGINEERED FOR THE TEAM. BUILT FOR THE NEXT LAP.</p></section>
    <main className="login-main"><div className="login-card"><div className="login-icon"><LockKeyhole size={24}/></div><span className="eyebrow">TECHNICIAN / ADMIN</span><h2>Welcome to the garage.</h2><p>Sign in with your team account to access Voltesse Dash.</p><form onSubmit={submit}><label htmlFor="username">Username or email</label><input id="username" autoComplete="username" value={username} onChange={e=>setUsername(e.target.value)} required maxLength={254} placeholder="Your team username"/><label htmlFor="password">Password</label><input id="password" type="password" autoComplete="current-password" value={password} onChange={e=>setPassword(e.target.value)} required maxLength={1024} placeholder="Enter your password"/>{error && <ErrorBox error={error}/>}<button className="primary" disabled={busy}>{busy?'Signing in…':'Sign in'}<ArrowUpRight size={18}/></button></form><div className="login-foot"><ShieldCheck size={16}/> Authorized team members only</div><p className="provision-note">Need an account? Ask your project administrator to provision one. No demo password is enabled.</p></div></main></div>;
}
const PAGES=[['Live','Live telemetry',Activity],['Diagnostics','Diagnostics',Wrench],['Sessions','Sessions',History],['Settings','Settings',Settings2],['Backups','Backups',Database]];
function Live({api,prefs}){
  const [t,setT]=useState(30),[playing,setPlaying]=useState(false);
  const {data,error}=useResource('live:'+t,()=>api('/live?t='+t),2000);
  useEffect(()=>{if(!playing)return;const id=setInterval(()=>setT(n=>{if(n>=120){setPlaying(false);return 120;}return n+1;}),1000);return()=>clearInterval(id);},[playing]);
  if(error)return <ErrorBox error={error}/>;if(!data)return <Loading/>;
  const m=data.metrics;
  const hot=m?.temperature!=null&&m.temperature>=prefs.warning_temp;
  const low=m?.battery!=null&&m.battery<=prefs.warning_battery;
  return <><div className="section-line"><div><h2>Vehicle overview</h2><p>Critical measurements, in one place.</p></div><span className={'pill '+(data.mode==='SIMULATION'?'amber':'')}><Radio size={13}/>{data.mode==='SIMULATION'?'SIMULATED':'DATABASE SOURCE'}</span></div>
    {data.mode==='SIMULATION' && <div className="simulation-bar"><div><strong>Simulation time</strong><span>{t} seconds · adjust the development scenario</span></div><input aria-label="Simulation time" type="range" min="0" max="120" value={t} onChange={e=>{setPlaying(false);setT(Number(e.target.value));}}/><button className="icon-button" onClick={()=>setPlaying(!playing)} aria-label={playing?'Pause simulation':'Play simulation'}>{playing?<Pause size={18}/>:<Play size={18}/>}</button></div>}
    {data.stale && <div className="notice danger"><AlertTriangle size={17}/>Telemetry is unavailable or older than 5 seconds. Displayed values are not current.</div>}
    <div className="metrics">{[['Speed',m?.speed,'MPH',Gauge],['Motor speed',m?.rpm,'RPM',Activity],['Battery',m?.battery,'%',Battery],['Motor temperature',m?.temperature,'°C',Thermometer],['Power draw',m?.power,'W',Zap]].map(([label,value,unit,Icon])=><section className="panel metric" key={label}><div className="metric-label">{label}<Icon size={19}/></div><div className="metric-value">{fmt(value,label==='Motor speed'||label==='Power draw'?0:1)}<small>{unit}</small></div><div className="metric-caption">{data.mode==='SIMULATION'?'Simulated reading':data.timestamp?date(data.timestamp):'No data'}</div></section>)}</div>
    <div className={'notice '+(hot||low?'danger':data.stale?'':'success')}>{hot||low?<AlertTriangle size={17}/>:data.stale?<Radio size={17}/>:<Check size={17}/>}<strong>{hot?'High motor temperature':low?'Low battery':data.stale?'Waiting for current telemetry':'Vehicle status: normal'}</strong><span>{hot&&low?'Low battery warning is also active.':`Warning limits: ${prefs.warning_temp} °C / ${prefs.warning_battery}% battery`}</span></div>
    <Plot title="Motor temperature" subtitle="Last 60 seconds · time (s) / temperature (°C)" data={data.history.map(r=>({x:Number(r.seconds),y:r.temperature}))} limit={prefs.warning_temp} height={285}/>
    <p className="footnote">{data.mode==='SIMULATION'?'Generated development data; these are not vehicle measurements or approved safety limits.':'Source: onboard telemetry database. Connection through the configured API.'}</p></>;
}
function Sessions({api,onSelect,selected}){
  const {data,error}=useResource('sessions',()=>api('/sessions'));
  if(error)return <ErrorBox error={error}/>;if(!data)return <Loading/>;
  return <><div className="section-line"><div><h2>Recent sessions</h2><p>Review the latest 20 recorded vehicle sessions.</p></div><span className="pill">{data.length} SESSIONS</span></div><section className="panel table-panel"><table><thead><tr>{['Session','Date','Duration','Max temperature','Source',''].map((h,i)=><th key={i}>{h}</th>)}</tr></thead><tbody>{data.map(s=><tr key={s.id} className={selected===s.id?'selected':''}><td><strong>#{s.id}</strong><small>{s.driver_identifier || 'Driver not specified'}</small></td><td>{date(s.start_timestamp)}</td><td>{duration(s.duration_seconds)}</td><td>{fmt(s.max_temp)} °C</td><td><span className={'pill '+(s.source_type==='SIMULATION'?'amber':'')}>{s.source_type}</span></td><td><button className="text-button" onClick={()=>onSelect(s.id)}>View diagnostics<ChevronRight size={15}/></button></td></tr>)}</tbody></table>{!data.length&&<div className="empty">No sessions yet. Record a run or explicitly seed the development fixtures.</div>}</section></>;
}
function Diagnostics({api,prefs,selected,onSelect}){
  const sessions=useResource('diagnostic-sessions',()=>api('/sessions'));
  const result=useResource('diagnostic:'+selected,()=>selected ? api(`/sessions/${selected}/diagnostics`):Promise.resolve(null));
  const charts=result.data?.charts;
  return <><div className="section-line"><div><h2>Performance analysis</h2><p>Five views of your selected session.</p></div><select aria-label="Select session" value={selected||''} onChange={e=>onSelect(Number(e.target.value)||null)}><option value="">Select a session</option>{sessions.data?.map(s=><option key={s.id} value={s.id}>Session #{s.id} · {s.source_type}</option>)}</select></div>
    {sessions.error&&<ErrorBox error={sessions.error}/>}{result.error&&<ErrorBox error={result.error}/>}
    {!selected?<div className="panel empty"><History size={28}/><h3>Select a recorded session</h3><p>Choose a session above or open one from Sessions.</p></div>:!charts&&!result.error?<Loading/>:charts&&<><div className="notice"><History size={17}/>Session #{selected}<span>{result.data.session.source_type==='SIMULATION'?'Simulated session data':'Recorded vehicle data'} · recorded session analysis</span></div><div className="diagnostic-grid"><Plot title="Energy efficiency vs. speed" subtitle="Speed (MPH) / consumption (Wh/mi)" data={charts.efficiency}/><Plot title="Power draw vs. temperature" subtitle="Motor temperature (°C) / power (W)" data={charts.power_temp}/><Plot title="Battery vs. distance" subtitle="Distance (mi) / battery remaining (%)" data={charts.battery} color="#398165"/><Plot title="Power draw vs. motor RPM" subtitle="Motor speed (RPM) / power (W)" data={charts.power_rpm} color="#ad5f85"/><Plot title="Temperature rise over time" subtitle="Operation time (min) / temperature (°C)" data={charts.temperature} limit={prefs.warning_temp}/></div></>}
  </>;
}
function Settings({api,prefs,onSaved}){
  const [draft,setDraft]=useState(prefs),[busy,setBusy]=useState(false),[message,setMessage]=useState(''),[error,setError]=useState(null);
  async function save(e){e.preventDefault();setBusy(true);setError(null);setMessage('');try{const value=await api('/settings',{method:'PUT',body:JSON.stringify(draft)});onSaved(value);setMessage('Warning settings saved to your account.');}catch(e){setError(e);}finally{setBusy(false);}}
  return <><div className="section-line"><div><h2>Dashboard settings</h2><p>Personal warning limits for the technician workspace.</p></div></div><form className="panel settings-panel" onSubmit={save}><div className="panel-heading"><h3>Warning thresholds</h3><Settings2 size={18}/></div><p>These settings affect this technician GUI only. They do not command the vehicle or change the Driver Dashboard.</p>{[['warning_temp','Motor temperature warning',40,110,'°C',Thermometer],['warning_battery','Low battery warning',5,40,'%',Battery]].map(([key,label,min,max,unit,Icon])=><div className="setting" key={key}><div><label htmlFor={key}><Icon size={18}/>{label}</label><strong>{draft[key]} {unit}</strong></div><input id={key} type="range" min={min} max={max} step={5} value={draft[key]} onChange={e=>{setDraft({...draft,[key]:Number(e.target.value)});setMessage('');}}/><div className="range-labels"><span>{min} {unit}</span><span>{max} {unit}</span></div></div>)}{error&&<ErrorBox error={error}/>}<div className="save-row"><button className="primary" disabled={busy}>{busy?'Saving…':'Save settings'}<Check size={16}/></button>{message&&<span role="status">{message}</span>}</div></form><p className="footnote">Development defaults are inherited from the Streamlit prototype. Confirm operational limits with the vehicle team.</p></>;
}
function Backups({api}){
  const [version,setVersion]=useState(0),[busy,setBusy]=useState(false),[error,setError]=useState(null),[success,setSuccess]=useState('');
  const result=useResource('backups:'+version,()=>api('/backups'));
  async function backup(){setBusy(true);setError(null);setSuccess('');try{const r=await api('/backups',{method:'POST'});setSuccess(`Backup #${r.backup_id} completed on the backend host.`);}catch(e){setError(e);}finally{setBusy(false);setVersion(n=>n+1);}}
  return <><div className="section-line"><div><h2>Database backups</h2><p>Create and review manual backups of the telemetry database.</p></div><button className="primary" disabled={busy} onClick={backup}><Download size={17}/>{busy?'Creating backup…':'Create backup'}</button></div><div className="notice"><ShieldCheck size={17}/>Backups remain on the backend host.<span>Includes account hashes. Access is restricted; files are never served publicly.</span></div>{error&&<ErrorBox error={error}/>} {success&&<div className="notice success" role="status"><Check size={17}/>{success}</div>}{result.error?<ErrorBox error={result.error}/>:!result.data?<Loading/>:<section className="panel table-panel"><table><thead><tr><th>Backup</th><th>Created</th><th>Type</th><th>Status</th></tr></thead><tbody>{result.data.map(b=><tr key={b.backup_id}><td>#{b.backup_id}</td><td>{date(b.backup_timestamp)}</td><td>{b.backup_type}</td><td><span className={'pill '+(b.backup_status==='FAILED'?'red':b.backup_status==='SUCCESS'?'green':'amber')}>{b.backup_status}</span></td></tr>)}</tbody></table>{!result.data.length&&<div className="empty">No backup records yet.</div>}</section>}</>;
}
export default function App(){
  const [user,setUser]=useState(null),[checking,setChecking]=useState(true),[page,setPage]=useState('Live'),[selected,setSelected]=useState(null),[prefs,setPrefs]=useState(null),[error,setError]=useState(null),[sessionError,setSessionError]=useState(null),[loggingOut,setLoggingOut]=useState(false);
  useEffect(()=>{request('/auth/me').then(setUser).catch(e=>{if(e.status!==401)setSessionError(e);}).finally(()=>setChecking(false));},[]);
  async function api(path,options){try{return await request(path,options,user?.csrf_token);}catch(e){if(e.status===401){setUser(null);setPrefs(null);setSelected(null);setPage('Live');setSessionError(new Error('Your session has expired. Please sign in again.'));}throw e;}}
  useEffect(()=>{let active=true;if(user)request('/settings').then(v=>{if(active)setPrefs(v);}).catch(e=>{if(active)setError(e);});return()=>{active=false;};},[user]);
  async function signOut(){setLoggingOut(true);setError(null);try{await api('/auth/logout',{method:'POST'});setUser(null);setPrefs(null);setSelected(null);setPage('Live');setSessionError(null);}catch(e){setError(e);}finally{setLoggingOut(false);}}
  if(checking)return <div className="startup"><Brand/><Loading/></div>;
  if(!user)return <Login initialError={sessionError} onLogin={u=>{setError(null);setSessionError(null);setUser(u);}}/>;
  return <div className="workspace"><aside className="sidebar"><Brand/><div className="sidebar-label">WORKSPACE</div><nav>{PAGES.map(([key,label,Icon])=><button key={key} className={page===key?'active':''} onClick={()=>setPage(key)}><Icon size={18}/>{label}{page===key&&<ChevronRight size={14}/>}</button>)}</nav><div className="sidebar-bottom"><div className="security-note"><ShieldCheck size={18}/><div>Authenticated access<span>Technician workspace</span></div></div><div className="account"><div className="avatar">{user.name.slice(0,1).toUpperCase()}</div><div><strong>{user.name}</strong><span>{user.role.toLowerCase()}</span></div><button aria-label="Sign out" title="Sign out" onClick={signOut} disabled={loggingOut}><LogOut size={18}/></button></div></div></aside><main className="content"><header><div><span className="eyebrow">VOLTESSE DASH / WORKSPACE</span><h1>{PAGES.find(p=>p[0]===page)[1]}</h1></div><div className="header-tag"><span/> TECHNICIAN / ADMIN</div></header><div className="page-content">{error&&<ErrorBox error={error}/>} {!prefs?<Loading/>:page==='Live'?<Live api={api} prefs={prefs}/>:page==='Sessions'?<Sessions api={api} selected={selected} onSelect={id=>{setSelected(id);setPage('Diagnostics');}}/>:page==='Diagnostics'?<Diagnostics api={api} prefs={prefs} selected={selected} onSelect={setSelected}/>:page==='Settings'?<Settings api={api} prefs={prefs} onSaved={setPrefs}/>:<Backups api={api}/>}</div><footer><span>VOLTESSE FORMULA ELECTRIC</span><span>Technician interface · laptop workspace</span></footer></main></div>;
}
