import React, {useEffect,useMemo,useRef,useState} from 'react';
import {createRoot} from 'react-dom/client';
import ReactMarkdown from 'react-markdown';
import TutorCodeBlock from './TutorCodeBlock'; import remarkGfm from 'remark-gfm'; import remarkMath from 'remark-math'; import rehypeKatex from 'rehype-katex'; import mermaid from 'mermaid';
import {Bell,Check,Globe,MapPin,Moon,Smartphone,Sun,BookOpen,BrainCircuit,ChartNoAxesCombined,ChevronDown,ChevronRight,CircleHelp,Clock3,FileText,FolderOpen,GraduationCap,LayoutDashboard,LogOut,Menu,MessageCircle,Plus,RefreshCw,Search,Send,Settings2,ShieldCheck,Sparkles,Target,Upload,Workflow,Bookmark,Lightbulb,Eye,CheckCircle2,LoaderCircle,PanelLeftClose,PanelLeftOpen,ArrowUpRight,Trash2,LibraryBig,CalendarDays, PencilLine, Download} from 'lucide-react';
import './styles.css';
import './feature-updates.css';
import './revision-redesign.css';
import './weekly-schedule-redesign.css';
import './weak-topics-redesign.css';
import './saved-visuals-redesign.css';
import './auth-redesign.css';
import './dashboard-redesign.css';
import './tutor-redesign.css';
import './quiz-redesign.css';
import './workspace-redesign.css';
import './progress-redesign.css';
import './whatsapp-reminders-redesign.css';
const API=(import.meta as any).env.VITE_API_URL||'';

// A shareable ?fresh=1 URL starts at login, even in a browser
// that already has a saved CogniGraph session.
if (
  typeof window !== "undefined" &&
  new URLSearchParams(window.location.search).get("fresh") === "1"
) {
  localStorage.removeItem("cg-token");
  localStorage.removeItem("cg-course");

  const cleanUrl = new URL(window.location.href);
  cleanUrl.searchParams.delete("fresh");
  window.history.replaceState(
    {},
    "",
    cleanUrl.pathname + cleanUrl.search + cleanUrl.hash
  );
}

type Course={id:number;name:string;description?:string}; type User={id:number;username:string};
async function request(path:string, token:string, init:RequestInit={}){const headers:any={...(init.body instanceof FormData?{}:{'Content-Type':'application/json'}),...(init.headers||{})};if(token)headers.Authorization=`Bearer ${token}`;const r=await fetch(API+path,{...init,headers});let data:any={};try{data=await r.json()}catch{}if(!r.ok)throw new Error(data.detail||`Request failed (${r.status})`);return data}
const nav=[{id:'home',label:'Overview',icon:LayoutDashboard,group:'LEARN'},{id:'tutor',label:'Socratic Tutor',icon:MessageCircle,group:'LEARN'},{id:'quiz',label:'Quiz Mode',icon:CircleHelp,group:'LEARN'},{id:'revision',label:'Revision Mode',icon:BookOpen,group:'LEARN'},{id:'weak',label:'Weak Topics',icon:Target,group:'LEARN'},{id:'schedule',label:'Weekly Study Schedule',icon:CalendarDays,group:'LEARN'},{id:'workspace',label:'Course Workspace',icon:FolderOpen,group:'WORKSPACE'},{id:'saved',label:'Saved Visuals',icon:Bookmark,group:'WORKSPACE'},{id:'progress',label:'Progress',icon:ChartNoAxesCombined,group:'WORKSPACE'},{id:'reminders',label:'WhatsApp Reminders',icon:MessageCircle,group:'WORKSPACE'}];
function App(){const [token,setToken]=useState(localStorage.getItem('cg-token')||'');const [user,setUser]=useState<User|null>(null);const [courses,setCourses]=useState<Course[]>([]);const [courseId,setCourseId]=useState(Number(localStorage.getItem('cg-course')||0));const [page,setPage]=useState('home');const [weakTargetTopic,setWeakTargetTopic]=useState('');const [practiceWeakTopics,setPracticeWeakTopics]=useState(false);useEffect(()=>{if(page!=='revision'&&page!=='quiz')setWeakTargetTopic('');if(page!=='quiz')setPracticeWeakTopics(false)},[page]);const [collapsed,setCollapsed]=useState(false);const [mobileNav,setMobileNav]=useState(false);const [busy,setBusy]=useState(false);const [error,setError]=useState('');const [toast,setToast]=useState('');
const notify=(s:string)=>{setToast(s);setTimeout(()=>setToast(''),3000)};
const loadMe=async(t:string)=>{const d=await request('/api/me',t);const available:Course[]=d.courses||[];setUser(d.user);setCourses(available);if(available.length){const selected=available.some(c=>c.id===courseId)?courseId:available[0].id;setCourseId(selected);localStorage.setItem('cg-course',String(selected))}else{setCourseId(0);localStorage.removeItem('cg-course');setPage('workspace')}};
useEffect(()=>{if(token)loadMe(token).catch(()=>{localStorage.removeItem('cg-token');setToken('');setUser(null)})},[token]);useEffect(()=>{if(courseId)localStorage.setItem('cg-course',String(courseId))},[courseId]);
const logout=async()=>{try{await request('/api/auth/logout',token,{method:'POST'})}catch{}localStorage.removeItem('cg-token');setToken('');setUser(null);setCourses([])};
if(!token||!user)return <Auth onSuccess={(d)=>{localStorage.setItem('cg-token',d.token);setToken(d.token);setUser(d.user);setCourses(d.courses||[]);if(d.courses?.length){setCourseId(d.courses[0].id)}else{setCourseId(0);localStorage.removeItem('cg-course');setPage('workspace')}}}/>;
const currentCourse=courses.find(c=>c.id===courseId)||courses[0];
return <div className={`shell cg-dark-dashboard ${collapsed?'is-collapsed':''}`}>
<aside className={`sidebar ${mobileNav?'mobile-open':''}`}><div className="brand"><div className="brand-mark"><BrainCircuit size={23}/></div>{!collapsed&&<div><b>CogniGraph</b><span>SOCRATIC LEARNING</span></div>}<button className="icon-button sidebar-toggle" onClick={()=>setCollapsed(!collapsed)} title="Collapse sidebar">{collapsed?<PanelLeftOpen size={17}/>:<PanelLeftClose size={17}/>}</button></div>
<div className="course-select"><div className="tiny-label">ACTIVE COURSE</div><div className="select-wrap"><LibraryBig size={17}/><select value={currentCourse?.id||''} disabled={!courses.length} onChange={e=>setCourseId(Number(e.target.value))}>{!courses.length&&<option value="">No courses yet</option>}{courses.map(c=><option value={c.id} key={c.id}>{c.name}</option>)}</select><ChevronDown size={14}/></div></div>
{['LEARN','WORKSPACE'].map(g=><div className="nav-group" key={g}><div className="nav-heading">{!collapsed&&g}</div>{nav.filter(n=>n.group===g).map(n=><button key={n.id} disabled={courses.length===0&&n.id!=='workspace'&&n.id!=='reminders'&&n.id!=='tutor'} className={`nav-item ${page===n.id?'active':''}`} onClick={()=>{setPage(n.id);setMobileNav(false);setError('')}} title={n.label}><n.icon size={18}/>{!collapsed&&<span>{n.label}</span>}{!collapsed&&page===n.id&&<ChevronRight size={15} className="nav-arrow"/>}</button>)}</div>)}
<div className="sidebar-bottom"><div className="status-card"><span className="status-dot"/>{!collapsed&&<div><b>Learning workspace</b><small>Course data stays scoped</small></div>}</div><button className="nav-item" onClick={logout}><LogOut size={18}/>{!collapsed&&<span>Sign out</span>}</button><div className="profile"> <div className="avatar">{user.username.slice(0,1).toUpperCase()}</div>{!collapsed&&<div className="profile-meta"><b>{user.username}</b><small>Student account</small></div>}</div></div></aside>
<main className="main"><header className="topbar"><button className="icon-button mobile-menu" onClick={()=>setMobileNav(!mobileNav)}><Menu/></button><div className="breadcrumbs">Workspace <ChevronRight size={14}/><b>{nav.find(n=>n.id===page)?.label||'Overview'}</b></div><div className="top-actions"><div className="course-pill"><span className="status-dot"/>{currentCourse?.name||'Select course'}</div><button className="secondary small top-logout" onClick={logout} title="Sign out"><LogOut size={14}/> Sign out</button><button className="avatar avatar-small" title={user.username}>{user.username.slice(0,1).toUpperCase()}</button></div></header>
<div className="content">{error&&<div className="alert error">{error}<button onClick={()=>setError('')}>×</button></div>}
{courses.length===0&&page!=='reminders'&&page!=='tutor'&&<Workspace token={token} courseId={courseId} courses={courses} setCourses={setCourses} setCourseId={setCourseId} notify={notify}/>}{courses.length>0&&page==='home'&&<Dashboard token={token} courseId={courseId} course={currentCourse} setPage={setPage}/>}
{page==='tutor'&&<Tutor token={token} courseId={courses.length>0?courseId:null} notify={notify}/>}
{courses.length>0&&page==='quiz'&&<Quiz token={token} courseId={courseId} notify={notify} initialTopic={weakTargetTopic} practiceWeakTopics={practiceWeakTopics}/>}
{courses.length>0&&page==='schedule'&&<WeeklySchedule token={token} courseId={courseId}/>} {courses.length>0&&page==='revision'&&<Revision token={token} courseId={courseId} initialTopic={weakTargetTopic}/>}
{courses.length>0&&page==='weak'&&<Weak token={token} courseId={courseId} setPage={setPage} setWeakTargetTopic={setWeakTargetTopic} setPracticeWeakTopics={setPracticeWeakTopics}/>}
{courses.length>0&&page==='workspace'&&<Workspace token={token} courseId={courseId} courses={courses} setCourses={setCourses} setCourseId={setCourseId} notify={notify}/>}
{courses.length>0&&page==='saved'&&<Saved token={token} courseId={courseId} notify={notify} setPage={setPage}/>}
{courses.length>0&&page==='progress'&&<Progress token={token} courseId={courseId} setPage={setPage}/>}{page==='reminders'&&<WhatsAppReminders token={token}/>}
</div></main>{toast&&<div className="toast"><CheckCircle2 size={17}/>{toast}</div>}</div>}
function Auth({onSuccess}:{onSuccess:(d:any)=>void}){
  const [mode,setMode]=useState<'login'|'register'>('login');
  const [username,setUsername]=useState('');
  const [password,setPassword]=useState('');
  const [showPassword,setShowPassword]=useState(false);
  const [busy,setBusy]=useState(false);
  const [err,setErr]=useState('');
  const [question,setQuestion]=useState('');
  const canvasRef=useRef<HTMLCanvasElement>(null);

  useEffect(()=>{
    const questions=[
      'If you doubled the learning rate, what would you expect to happen to the loss curve?',
      'Why might a model score perfectly on training data and still fail on new data?',
      'What does attention let a model do that a fixed window could not?'
    ];
    if(window.matchMedia('(prefers-reduced-motion: reduce)').matches){
      setQuestion(questions[0]);
      return;
    }
    let qi=0,ci=0,timer=0;
    const tick=()=>{
      const current=questions[qi];
      if(ci<=current.length){
        setQuestion(current.slice(0,ci++));
        timer=window.setTimeout(tick,28);
      }else{
        timer=window.setTimeout(()=>{
          ci=0;
          qi=(qi+1)%questions.length;
          tick();
        },3200);
      }
    };
    tick();
    return ()=>window.clearTimeout(timer);
  },[]);

  useEffect(()=>{
    const canvas=canvasRef.current;
    const ctx=canvas?.getContext('2d');
    if(!canvas||!ctx)return;

    const stage=canvas.parentElement;
    const reduced=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const names=['Gradient','Loss','Backprop','Overfitting','Attention',
      'Embeddings','Bias','Regularization','Tokens','Softmax','Layers','Dropout'];
    const colors=['#B8AFFF','#5EEAD4','#FFC86B'];
    let width=0,height=0,raf=0;
    let nodes:any[]=[];
    const mouse={x:-999,y:-999};
    const dpr=Math.min(window.devicePixelRatio||1,2);

    function resize(){
      const r=canvas!.getBoundingClientRect();
      width=r.width;height=r.height;
      canvas!.width=Math.max(1,Math.round(width*dpr));
      canvas!.height=Math.max(1,Math.round(height*dpr));
      ctx!.setTransform(dpr,0,0,dpr,0,0);
      const count=width<700?16:30;
      nodes=Array.from({length:count},(_,i)=>({
        x:Math.random()*width,y:Math.random()*height,
        vx:(Math.random()-.5)*.22,vy:(Math.random()-.5)*.22,
        r:i<names.length?5.5:2.6,
        color:colors[i%3],label:i<names.length?names[i]:null,
        phase:Math.random()*6
      }));
    }

    function draw(t:number){
      ctx!.clearRect(0,0,width,height);
      for(let i=0;i<nodes.length;i++){
        const a=nodes[i];
        if(!reduced){
          a.x+=a.vx;a.y+=a.vy;
          if(a.x<0||a.x>width)a.vx*=-1;
          if(a.y<0||a.y>height)a.vy*=-1;
        }
        for(let j=i+1;j<nodes.length;j++){
          const b=nodes[j],dx=a.x-b.x,dy=a.y-b.y;
          const dist=Math.sqrt(dx*dx+dy*dy);
          if(dist<150){
            const mx=(a.x+b.x)/2-mouse.x;
            const my=(a.y+b.y)/2-mouse.y;
            const near=Math.sqrt(mx*mx+my*my)<130;
            ctx!.strokeStyle=near
              ?`rgba(94,234,212,${.75*(1-dist/150)})`
              :`rgba(184,175,255,${.3*(1-dist/150)})`;
            ctx!.lineWidth=near?1.6:1;
            ctx!.beginPath();ctx!.moveTo(a.x,a.y);
            ctx!.lineTo(b.x,b.y);ctx!.stroke();
          }
        }
      }
      ctx!.font='500 12px "DM Sans",sans-serif';
      ctx!.textBaseline='middle';
      for(const n of nodes){
        const dx=n.x-mouse.x,dy=n.y-mouse.y;
        const hot=Math.sqrt(dx*dx+dy*dy)<90;
        const pulse=reduced?0:Math.sin(t/900+n.phase)*.8;
        ctx!.fillStyle=n.color;
        ctx!.globalAlpha=n.label?1:.55;
        ctx!.beginPath();
        ctx!.arc(n.x,n.y,n.r+pulse+(hot?2:0),0,Math.PI*2);
        ctx!.fill();ctx!.globalAlpha=1;
        if(n.label&&width>700){
          ctx!.fillStyle=hot?'#fff':'rgba(237,234,255,.7)';
          ctx!.fillText(n.label,n.x+n.r+7,n.y);
        }
      }
      if(!reduced)raf=requestAnimationFrame(draw);
    }

    const onMouseMove=(e:MouseEvent)=>{
      const r=canvas!.getBoundingClientRect();
      mouse.x=e.clientX-r.left;mouse.y=e.clientY-r.top;
    };
    const onMouseLeave=()=>{mouse.x=mouse.y=-999};
    const onResize=()=>{resize();if(reduced)draw(0)};

    resize();draw(0);
    stage?.addEventListener('mousemove',onMouseMove);
    stage?.addEventListener('mouseleave',onMouseLeave);
    window.addEventListener('resize',onResize);
    return ()=>{
      cancelAnimationFrame(raf);
      stage?.removeEventListener('mousemove',onMouseMove);
      stage?.removeEventListener('mouseleave',onMouseLeave);
      window.removeEventListener('resize',onResize);
    };
  },[]);

  async function submit(e:React.FormEvent<HTMLFormElement>){
    e.preventDefault();
    if(busy)return;

    const started=Date.now();
    setBusy(true);
    setErr('');

    async function keepSpinnerVisible(){
      const remaining=500-(Date.now()-started);
      if(remaining>0){
        await new Promise(resolve=>window.setTimeout(resolve,remaining));
      }
    }

    try{
      const response=await fetch(`${API}/api/auth/${mode}`,{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({username:username.trim(),password})
      });
      let data:any={};
      try{data=await response.json()}catch{}
      if(!response.ok){
        throw new Error(data.detail||(
          mode==='login'?'Unable to sign in.':'Unable to create your account.'
        ));
      }
      await keepSpinnerVisible();
      onSuccess(data);
    }catch(e:any){
      await keepSpinnerVisible();
      setErr(e.message||'Unable to connect. Please try again.');
    }finally{
      setBusy(false);
    }
  }

  function changeMode(next:'login'|'register'){
    if(busy)return;
    setMode(next);
    setErr('');
  }

  return <div className="cg-auth">
    <div className="cg-auth-page">
      <section className="cg-stage" aria-label="About CogniGraph">
        <canvas ref={canvasRef} className="cg-graph" aria-hidden="true"/>

        <div className="cg-stage-top">
          <div className="cg-brand">
            <svg className="cg-mark" viewBox="0 0 56 56" fill="none" aria-hidden="true">
              <rect width="56" height="56" rx="16" fill="#6C5CE7"/>
              <path d="M16 38 28 16l12 22M20.5 31h15" stroke="#fff"
                strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" opacity=".55"/>
              <circle cx="16" cy="38" r="5" fill="#fff"/>
              <circle cx="28" cy="16" r="5" fill="#5EEAD4"/>
              <circle cx="40" cy="38" r="5" fill="#FFC86B"/>
            </svg>
            <div className="cg-wordmark">Cogni<span>Graph</span></div>
          </div>
          <p className="cg-tag">A Socratic tutor. Thinking comes first.</p>
        </div>

        <div className="cg-thinking-scene">
          <svg className="cg-thinker" viewBox="0 0 110 110"
            role="img" aria-label="Illustration of a student thinking">
            <g fill="none" stroke="#B8AFFF" strokeWidth="1.3" opacity=".65">
              <path d="M15 17 35 35 16 60"/>
              <path d="M68 21 91 35 80 57"/>
              <path d="M15 60 38 77 68 91"/>
              <path d="M68 21 68 5"/>
            </g>
            <circle cx="15" cy="17" r="4.1" fill="#B8AFFF"/>
            <circle cx="91" cy="35" r="4.1" fill="#B8AFFF"/>
            <circle cx="80" cy="57" r="3" fill="#5EEAD4"/>
            <circle cx="68" cy="5" r="4" fill="#FFC86B"/>
            <circle cx="68" cy="91" r="3" fill="#5EEAD4"/>
            <circle cx="38" cy="77" r="3" fill="#B8AFFF"/>
            <path d="M28 91c2-17 12-26 27-26s25 9 27 26v7H28z" fill="#6C5CE7"/>
            <path d="M44 63v11c5 5 12 5 17 0V63" fill="#E8B28F"/>
            <ellipse cx="55" cy="43" rx="17" ry="21" fill="#F3C8A4"/>
            <path d="M38 42c-2-14 5-25 18-25 12 0 18 9 17 23l-5-8-8-5-13 4z" fill="#342A49"/>
            <path d="M42 32c5-8 19-10 27-2" fill="none" stroke="#342A49" strokeWidth="5" strokeLinecap="round"/>
            <circle cx="49" cy="43" r="1.6" fill="#342A49"/>
            <circle cx="61" cy="43" r="1.6" fill="#342A49"/>
            <path d="M51 54c3 2 6 2 9 0" fill="none" stroke="#A85E61" strokeWidth="1.5" strokeLinecap="round"/>
            <path d="M42 70c4 8 21 8 26 0" fill="none" stroke="#B8AFFF" strokeWidth="1.5" strokeLinecap="round"/>
          </svg>

          <div className="cg-thought-bubble" aria-live="polite">
            <strong>Thinking<span className="cg-thinking-dots">...</span></strong>
            <p><span>{question}</span><span className="cg-caret"/></p>
          </div>
        </div>

        <div className="cg-claim">
          <h2>Learn by thinking.</h2>
          <p className="cg-description">
            Your tutor won’t hand you the answer. It asks the question that helps you reason your way there.
          </p>
          <div className="cg-points">
            <span><ShieldCheck size={14}/> Answers come from your own course material</span>
            <span><Workflow size={14}/> Every concept shown as a visual map</span>
          </div>
        </div>
      </section>

      <main className="cg-panel">
        <div className="cg-card">
          <div className="cg-mini-brand">Cogni<span>Graph</span></div>
          <div className="cg-tabs" role="tablist" aria-label="Authentication options">
            <button type="button" role="tab" id="cg-tab-in"
              aria-selected={mode==='login'} disabled={busy}
              onClick={()=>changeMode('login')}>Sign in</button>
            <button type="button" role="tab" id="cg-tab-up"
              aria-selected={mode==='register'} disabled={busy}
              onClick={()=>changeMode('register')}>Create account</button>
          </div>

          <h1>{mode==='login'?'Welcome back':'Start learning by thinking'}</h1>
          <p className="cg-sub">
            {mode==='login'
              ?'Pick up where your last question left off.'
              :'Create an account to keep your courses and progress.'}
          </p>

          <form onSubmit={submit} aria-busy={busy}>
            <div className="cg-field">
              <label htmlFor="cg-username">Username</label>
              <input className="cg-input" id="cg-username"
                autoComplete="username" required disabled={busy}
                value={username} onChange={e=>setUsername(e.target.value)}
                placeholder="Enter your username"/>
            </div>

            <div className="cg-field cg-password-field">
              <label htmlFor="cg-password">Password</label>
              <input className="cg-input" id="cg-password"
                type={showPassword?'text':'password'}
                autoComplete={mode==='login'?'current-password':'new-password'}
                minLength={6} required disabled={busy}
                value={password} onChange={e=>setPassword(e.target.value)}
                placeholder="At least 6 characters"/>
              <button className="cg-eye" type="button"
                disabled={busy}
                onClick={()=>setShowPassword(v=>!v)}
                aria-label={showPassword?'Hide password':'Show password'}>
                <Eye size={15}/>{showPassword?'Hide':'Show'}
              </button>
            </div>

            {err&&<div className="cg-message cg-error" role="alert">{err}</div>}

            <button className="cg-go" type="submit" disabled={busy}
              aria-live="polite">
              {busy
                ?<><LoaderCircle className="cg-spinner" size={18}/>
                   {mode==='login'?'Signing in…':'Creating account…'}</>
                :mode==='login'?'Sign in':'Create account'}
            </button>
          </form>

          <div className="cg-message" role="status">
            {busy?'Please wait while we securely verify your details.':''}
          </div>

          <div className="cg-foot">
            <ShieldCheck size={16}/>
            Your courses stay private to your account.
          </div>
        </div>
      </main>
    </div>
  </div>;
}

function WhatsAppReminders({token}:any){
  const [phone,setPhone]=useState('');
  const [enabled,setEnabled]=useState(false);
  const [timezone,setTimezone]=useState('Asia/Karachi');
  const [reminderTime,setReminderTime]=useState('19:00');
  const [consent,setConsent]=useState(false);
  const [loading,setLoading]=useState(true);
  const [saving,setSaving]=useState(false);
  const [err,setErr]=useState('');
  const [saved,setSaved]=useState('');

  const normalizedPhone=phone.replace(/[\s()-]/g,'');
  const phoneValid=/^\+[1-9]\d{7,14}$/.test(normalizedPhone);
  const canEnable=phoneValid&&consent&&!loading&&!saving;

  function formatTime(value:string){
    const [rawHour,rawMinute='00']=String(value||'').split(':');
    const hour=Number(rawHour),minute=Number(rawMinute);
    if(!Number.isFinite(hour)||!Number.isFinite(minute))return '--:--';
    return `${((hour+11)%12)+1}:${String(minute).padStart(2,'0')} ${hour>=12?'PM':'AM'}`;
  }

  useEffect(()=>{
    let active=true;
    request('/api/me/whatsapp-reminders',token)
      .then((d:any)=>{
        if(!active)return;
        const p=d.preferences||{};
        setPhone(p.phone_number||'');
        setEnabled(Boolean(p.enabled));
        setTimezone(p.timezone||'Asia/Karachi');
        setReminderTime(p.reminder_time||'19:00');
        setConsent(Boolean(p.consent));
      })
      .catch((e:any)=>{if(active)setErr(e.message||'Could not load reminder preferences. You can still explore the form.')})
      .finally(()=>{if(active)setLoading(false)});
    return()=>{active=false};
  },[token]);

  async function save(e:React.FormEvent<HTMLFormElement>){
    e.preventDefault();
    setErr('');
    setSaved('');
    if(enabled&&!phoneValid){setErr('Enter a valid international WhatsApp number, including + and your country code.');return;}
    if(enabled&&!consent){setErr('Please give consent before enabling reminders.');return;}
    try{
      setSaving(true);
      const d=await request('/api/me/whatsapp-reminders',token,{
        method:'PUT',
        body:JSON.stringify({
          phone_number:phone.trim(),
          enabled:enabled&&consent&&phoneValid,
          timezone:timezone.trim(),
          reminder_time:reminderTime,
          consent
        })
      });
      const p=d.preferences||{};
      setPhone(p.phone_number||'');
      setEnabled(Boolean(p.enabled));
      setTimezone(p.timezone||'Asia/Karachi');
      setReminderTime(p.reminder_time||'19:00');
      setConsent(Boolean(p.consent));
      setSaved(p.enabled
        ?'Preferences saved. Delivery is in dry-run mode; no WhatsApp message was sent.'
        :'Preferences saved. WhatsApp reminders are currently off.');
    }catch(e:any){
      setErr(e.message||'Could not save reminder preferences.');
    }finally{
      setSaving(false);
    }
  }

  function chooseTime(value:string){setReminderTime(value);setSaved('');}
  function detectTimezone(){
    try{
      const detected=Intl.DateTimeFormat().resolvedOptions().timeZone;
      if(detected)setTimezone(detected);
      setSaved(detected?`Time zone detected: ${detected}`:'Could not detect a time zone on this device.');
    }catch{setSaved('Could not detect a time zone on this device.');}
  }
  function testMessage(){
    setErr('');
    if(!phoneValid){setSaved('Enter a valid international WhatsApp number first.');return;}
    if(!consent){setSaved('Please agree to reminders before requesting a test message.');return;}
    setSaved('Demo only: WhatsApp delivery is not connected yet, so no test message was sent.');
  }

  return <div className="cg-reminders-page">
    <section className="cg-r-hero">
      <svg className="cg-r-network" viewBox="0 0 900 200" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
        <g stroke="#B8AFFF" strokeOpacity=".34" fill="none"><path d="M70 40 200 110 150 180M200 110 360 50 470 140 360 190M470 140 620 50 760 130 860 40"/></g>
        <g><circle cx="70" cy="40" r="5" fill="#B8AFFF"/><circle cx="200" cy="110" r="7" fill="#5EEAD4"/><circle cx="360" cy="50" r="6" fill="#B8AFFF"/><circle cx="470" cy="140" r="8" fill="#FFC86B"/><circle cx="620" cy="50" r="5" fill="#5EEAD4"/><circle cx="760" cy="130" r="6" fill="#B8AFFF"/></g>
      </svg>
      <div className="cg-r-hero-copy">
        <span className="cg-r-kicker">STUDY ROUTINE · PERSONAL SETTINGS</span>
        <h1>Never miss a session.</h1>
        <p>A friendly nudge on WhatsApp, right on time.</p>
      </div>
      <div className="cg-r-thinking" aria-label="A reminder to choose a realistic study time">
        <svg className="cg-r-thinker" viewBox="0 0 120 132" fill="none" aria-hidden="true">
          <path d="M12 132C12 102 34 90 60 90s48 12 48 42z" fill="#6C5CE7"/><rect x="53" y="76" width="14" height="17" rx="5" fill="#E8B98F"/><ellipse cx="60" cy="52" rx="22" ry="26" fill="#F2C9A5"/><path d="M37 52c-4-24 12-32 25-31 17 1 24 14 21 31-5-12-15-16-27-15-9 1-15 6-19 15z" fill="#4A3FB0"/><path d="M47 46q5-3 10 0M64 44q5-3 10 0" stroke="#2A2166" strokeWidth="2" strokeLinecap="round"/><circle cx="54" cy="52" r="2.6" fill="#120F2E"/><circle cx="71" cy="50" r="2.6" fill="#120F2E"/><path d="M55 66q5-2 9 0" stroke="#9A5B4A" strokeWidth="2" strokeLinecap="round"/><path d="M92 126 84 98 70 76" stroke="#6C5CE7" strokeWidth="14" strokeLinecap="round" strokeLinejoin="round"/><circle cx="68" cy="72" r="8" fill="#F2C9A5"/>
        </svg>
        <div className="cg-r-thought"><b>Ask yourself</b><span>What time will you actually open it?</span></div>
      </div>
    </section>

    <section className="cg-r-stats" aria-label="Reminder summary">
      <div className={`cg-r-stat cg-r-stat-status ${enabled?'is-on':'is-off'}`}>
        <span className="cg-r-stat-icon"><Bell size={18}/></span><div><b>{enabled?'Reminders on':'Reminders off'}</b><small>Status · {consent?'Consent recorded':'Consent not given'}</small></div>
      </div>
      <div className="cg-r-stat cg-r-stat-time">
        <span className="cg-r-stat-icon"><Clock3 size={18}/></span><div><b>{formatTime(reminderTime)}</b><small>Preferred time · Daily</small></div>
      </div>
      <div className="cg-r-stat cg-r-stat-zone">
        <span className="cg-r-stat-icon"><Globe size={18}/></span><div><b>{timezone||'Time zone not set'}</b><small>Time zone</small></div>
      </div>
    </section>

    <div className="cg-r-layout">
      <section className="cg-r-card cg-r-preferences">
        <div className="cg-r-card-heading"><span className="cg-r-heading-icon"><Bell size={18}/></span><div><h2>Study reminder preferences</h2><p>Choose a time that fits your real study routine.</p></div></div>
        {loading&&<div className="cg-r-loading" role="status">Loading your saved preferences…</div>}
        <form onSubmit={save}>
          <label className="cg-r-label" htmlFor="cg-r-phone"><Smartphone size={15}/> WhatsApp number</label>
          <div className={`cg-r-field ${phoneValid?'is-valid':phone.trim()?'is-invalid':''}`}>
            <Smartphone size={17}/><input id="cg-r-phone" type="tel" inputMode="tel" autoComplete="tel" placeholder="+92 300 1234567" value={phone} disabled={loading||saving} onChange={e=>{setPhone(e.target.value);setSaved('');}} aria-describedby="cg-r-phone-help"/><span className="cg-r-valid-icon" aria-hidden="true"><Check size={14}/></span>
          </div>
          <p id="cg-r-phone-help" className={`cg-r-help ${phone.trim()&&!phoneValid?'is-error':''}`}>{phoneValid?'Looks good.':phone.trim()?'Use + and 8 to 15 digits, for example +92 300 1234567.':'Use international format, including your country code.'}</p>

          <div className="cg-r-fields-two">
            <div>
              <label className="cg-r-label" htmlFor="cg-r-timezone"><Globe size={15}/> Time zone</label>
              <div className="cg-r-field cg-r-zone-field"><input id="cg-r-timezone" list="cg-r-timezones" value={timezone} disabled={loading||saving} onChange={e=>setTimezone(e.target.value)} required/><datalist id="cg-r-timezones"><option value="Asia/Karachi"/><option value="UTC"/><option value="Europe/London"/><option value="Asia/Dubai"/><option value="Asia/Kolkata"/><option value="America/New_York"/><option value="America/Los_Angeles"/><option value="Australia/Sydney"/></datalist><button className="cg-r-mini" type="button" onClick={detectTimezone} disabled={loading||saving}><MapPin size={13}/> Detect</button></div>
            </div>
            <div>
              <label className="cg-r-label" htmlFor="cg-r-time"><Clock3 size={15}/> Reminder time</label>
              <div className="cg-r-field"><input id="cg-r-time" type="time" value={reminderTime} required disabled={loading||saving} onChange={e=>chooseTime(e.target.value)}/><Clock3 size={16}/></div>
            </div>
          </div>
          <div className="cg-r-presets" aria-label="Quick reminder times">
            <button type="button" className={reminderTime==='08:00'?'is-active':'cg-r-preset-morning'} aria-pressed={reminderTime==='08:00'} onClick={()=>chooseTime('08:00')}><Sun size={14}/> Morning</button>
            <button type="button" className={reminderTime==='13:00'?'is-active':'cg-r-preset-afternoon'} aria-pressed={reminderTime==='13:00'} onClick={()=>chooseTime('13:00')}><Sun size={14}/> Afternoon</button>
            <button type="button" className={reminderTime==='19:00'?'is-active':'cg-r-preset-evening'} aria-pressed={reminderTime==='19:00'} onClick={()=>chooseTime('19:00')}><Moon size={14}/> Evening</button>
            <button type="button" className={reminderTime==='21:00'?'is-active':'cg-r-preset-night'} aria-pressed={reminderTime==='21:00'} onClick={()=>chooseTime('21:00')}><Moon size={14}/> Night</button>
          </div>

          <label className="cg-r-consent">
            <input type="checkbox" checked={consent} disabled={loading||saving} onChange={e=>{const checked=e.target.checked;setConsent(checked);if(!checked)setEnabled(false);setSaved('');}}/>
            <span className="cg-r-checkbox"><Check size={15}/></span>
            <span className="cg-r-consent-copy"><b><ShieldCheck size={15}/> I agree to get reminders</b><small>Recurring WhatsApp study reminders at this number. You can withdraw consent at any time.</small></span>
          </label>

          <div className="cg-r-toggle-row">
            <span className="cg-r-toggle-icon"><Bell size={17}/></span><div className="cg-r-toggle-copy"><b>Turn on reminders</b><small>{!phoneValid?'Enter a valid number to enable reminders.':!consent?'Your consent is required.':enabled?'Preference is switched on. Delivery is still in dry-run mode.':'Reminders are paused until you turn them on.'}</small></div>
            <button type="button" role="switch" aria-checked={enabled} aria-label="Enable study reminders" className={`cg-r-switch ${enabled?'is-on':''}`} disabled={!canEnable&& !enabled || loading||saving} onClick={()=>{setEnabled(v=>!v);setSaved('');}}><span/></button>
          </div>

          {err&&<div className="cg-r-message is-error" role="alert">{err}</div>}
          {saved&&<div className="cg-r-message" role="status">{saved}</div>}
          <button className="cg-r-save" type="submit" disabled={loading||saving}>{saving?'Saving preferences…':loading?'Loading preferences…':<><Check size={17}/> Save reminder preferences</>}</button>
          <div className="cg-r-privacy"><ShieldCheck size={16}/><span>Settings are saved to your CogniGraph account. Live WhatsApp delivery is not enabled yet.</span></div>
        </form>
      </section>

      <aside className="cg-r-preview-column">
        <div className="cg-r-phone-wrap">
          <div className="cg-r-phone" aria-label="Illustrative WhatsApp reminder preview">
            <div className="cg-r-phone-head"><span className="cg-r-phone-logo"><BrainCircuit size={18}/></span><span><b>CogniGraph</b><small>Study reminders · Preview</small></span></div>
            <div className="cg-r-phone-body"><span className="cg-r-day">Today · Preview</span><div className="cg-r-message-bubble"><b>CogniGraph</b><p>Time for your study session. Set aside 30 minutes to learn something new. Ready when you are.</p><time>{formatTime(reminderTime)}</time></div><div className="cg-r-quick-replies"><span>Start now</span><span>Remind me later</span></div></div>
          </div>
        </div>
        <div className="cg-r-preview-caption"><span className="cg-r-preview-dot"/> Example message preview only. It does not represent a delivered WhatsApp message.</div>
        <button className="cg-r-test" type="button" onClick={testMessage} disabled={loading||saving}><Send size={16}/> Send me a test message <span className="cg-r-demo-tag">Demo</span></button>
        <div className="cg-r-dry-run"><ShieldCheck size={17}/><p><b>Currently in dry-run mode.</b><br/>Saving preferences does not send a message. WhatsApp provider credentials and live delivery will be configured in a later backend phase.</p></div>
      </aside>
    </div>
  </div>;
}
function PageHeading({eyebrow,title,desc,action}:{eyebrow?:string;title:string;desc:string;action?:React.ReactNode}){return <div className="page-heading"><div>{eyebrow&&<div className="eyebrow">{eyebrow}</div>}<h1>{title}</h1><p>{desc}</p></div>{action}</div>}
function Metric({icon:Icon,label,value,sub,tint='blue'}:any){return <div className="metric-card"><div className={`metric-icon ${tint}`}><Icon size={19}/></div><div className="metric-label">{label}</div><div className="metric-value">{value??'—'}</div>{sub&&<div className="metric-sub">{sub}</div>}</div>}
function Dashboard({token,courseId,course,setPage}:any){
  const [data,setData]=useState<any>(null);
  const [weakData,setWeakData]=useState<any>(null);
  const [plan,setPlan]=useState<any>(null);
  const [reminders,setReminders]=useState<any>(null);
  const [loading,setLoading]=useState(true);
  const [loadError,setLoadError]=useState('');

  function localISO(d:Date){
    return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
  }

  function currentWeekStart(){
    const d=new Date();
    d.setHours(12,0,0,0);
    d.setDate(d.getDate()-((d.getDay()+6)%7));
    return localISO(d);
  }

  useEffect(()=>{
    let active=true;
    setLoading(true);
    setLoadError('');
    setData(null);
    setWeakData(null);
    setPlan(null);
    setReminders(null);

    if(!courseId){
      setLoading(false);
      return ()=>{active=false};
    }

    const weekStart=currentWeekStart();

    request(`/api/courses/${courseId}/dashboard`,token)
      .then((value:any)=>{if(active)setData(value)})
      .catch((e:any)=>{if(active)setLoadError(e.message||'Could not load dashboard data.')})
      .finally(()=>{if(active)setLoading(false)});

    request(`/api/courses/${courseId}/weak-topics`,token)
      .then((value:any)=>{if(active)setWeakData(value)})
      .catch(()=>{});

    request(`/api/courses/${courseId}/study-plan?week_start=${encodeURIComponent(weekStart)}`,token)
      .then((value:any)=>{if(active)setPlan(value?.study_plan||null)})
      .catch(()=>{});

    request('/api/me/whatsapp-reminders',token)
      .then((value:any)=>{if(active)setReminders(value?.preferences||null)})
      .catch(()=>{});

    return ()=>{active=false};
  },[token,courseId]);

  const weekStart=currentWeekStart();
  const weekDates=Array.from({length:7},(_,i)=>{
    const d=new Date(`${weekStart}T12:00:00`);
    d.setDate(d.getDate()+i);
    return d;
  });

  function decodePlan(value:any):any{
    if(typeof value!=='string')return value;
    try{return JSON.parse(value)}catch{return null}
  }

  function collectSessions(value:any):any[]{
    const candidates=[
      decodePlan(value),
      decodePlan(value?.plan),
      decodePlan(value?.plan_json),
      decodePlan(value?.study_plan),
      decodePlan(value?.study_plan?.plan),
      decodePlan(value?.study_plan?.plan_json)
    ];

    for(const item of candidates){
      if(Array.isArray(item))return item;
      if(Array.isArray(item?.sessions))return item.sessions;
      if(Array.isArray(item?.plan?.sessions))return item.plan.sessions;
      if(Array.isArray(item?.days)){
        return item.days.flatMap((day:any)=>
          Array.isArray(day?.sessions)
            ?day.sessions
            :day&&typeof day==='object'?[day]:[]
        );
      }
    }
    return [];
  }

  const sessions=collectSessions(plan);

  function sessionDate(session:any):string{
    const raw=String(session?.date||session?.session_date||session?.day_date||'');
    if(/^\d{4}-\d{2}-\d{2}/.test(raw))return raw.slice(0,10);

    const dayName=String(session?.day||session?.day_name||raw).toLowerCase();
    const names=['monday','tuesday','wednesday','thursday','friday','saturday','sunday'];
    const index=names.findIndex(name=>dayName.startsWith(name));
    return index>=0?localISO(weekDates[index]):'';
  }

  function isCompleted(session:any):boolean{
    return Boolean(
      session?.completed===true||
      session?.is_completed===true||
      session?.progress?.completed===true||
      session?.progress?.is_completed===true||
      String(session?.status||'').toLowerCase()==='completed'
    );
  }

  const daily=weekDates.map((date,index)=>{
    const iso=localISO(date);
    const rows=sessions.filter((session:any)=>sessionDate(session)===iso);
    const completed=rows.filter(isCompleted).length;
    const height=rows.length?Math.min(100,20+rows.length*20):15;
    return {
      iso,
      label:date.toLocaleDateString(undefined,{weekday:'short'}),
      isToday:iso===localISO(new Date()),
      total:rows.length,
      completed,
      height
    };
  });

  const completedSessions=sessions.filter(isCompleted).length;
  const activeDays=daily.filter(day=>day.completed>0).length;
  const weakTopics=(weakData?.topics||data?.weak_topics||[]).slice(0,3);
  const recent=(data?.recent||[]).slice(0,4);

  function timeAgo(value:any):string{
    if(value===null||value===undefined)return 'Recorded activity';
    const n=Number(value);
    if(!Number.isFinite(n))return 'Recorded activity';
    const ms=n<1000000000000?n*1000:n;
    const diff=Math.max(0,Date.now()-ms);
    const minutes=Math.floor(diff/60000);
    if(minutes<1)return 'Just now';
    if(minutes<60)return `${minutes} min ago`;
    const hours=Math.floor(minutes/60);
    if(hours<24)return `${hours} hr ago`;
    const days=Math.floor(hours/24);
    if(days===1)return 'Yesterday';
    if(days<7)return `${days} days ago`;
    return new Date(ms).toLocaleDateString();
  }

  function reminderTime(value:any):string{
    const parts=String(value||'19:00').split(':');
    const hours=Number(parts[0]);
    const minutes=Number(parts[1]||0);
    if(!Number.isFinite(hours)||!Number.isFinite(minutes))return String(value||'19:00');
    const h=((hours+11)%12)+1;
    return `${h}:${String(minutes).padStart(2,'0')} ${hours>=12?'PM':'AM'}`;
  }

  function ActivityIcon({event}:any){
    const name=String(event||'').toLowerCase();
    if(name.includes('quiz'))return <CircleHelp size={16}/>;
    if(name.includes('upload')||name.includes('source'))return <FolderOpen size={16}/>;
    if(name.includes('revision'))return <BookOpen size={16}/>;
    return <MessageCircle size={16}/>;
  }

  return <div className="cg-dash">
    <div className="cg-dash-grid">
      <section className="cg-dash-hero cg-dash-span-8">
        <svg className="cg-hero-network" viewBox="0 0 600 260" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
          <g stroke="#B8AFFF" strokeOpacity=".32" fill="none">
            <path d="M60 40 180 110 120 200M180 110 330 60 430 150 330 220M430 150 560 70M330 60 330 220"/>
          </g>
          <g>
            <circle cx="60" cy="40" r="5" fill="#B8AFFF"/>
            <circle cx="180" cy="110" r="7" fill="#5EEAD4"/>
            <circle cx="120" cy="200" r="4" fill="#FFC86B"/>
            <circle cx="330" cy="60" r="6" fill="#B8AFFF"/>
            <circle cx="430" cy="150" r="8" fill="#FFC86B"/>
            <circle cx="330" cy="220" r="5" fill="#5EEAD4"/>
            <circle cx="560" cy="70" r="4" fill="#B8AFFF"/>
          </g>
        </svg>

        <div className="cg-hero-copy">
          <div className="cg-dash-kicker">YOUR LEARNING SPACE</div>
          <h1>Good to see you again.</h1>
          <p>Pick up where you left off in {course?.name||'your course'}.</p>
          <div className="cg-hero-buttons">
            <button className="cg-btn-mint" onClick={()=>setPage('tutor')}>
              <Sparkles size={15}/> Start learning
            </button>
            <button className="cg-btn-glass" onClick={()=>setPage('tutor')}>
              <Plus size={15}/> New session
            </button>
          </div>
        </div>

        <div className="cg-hero-thinking" aria-hidden="true">
          <svg className="cg-thinking-person" viewBox="0 0 120 132" fill="none">
            <path d="M12 132C12 102 34 90 60 90s48 12 48 42z" fill="#6C5CE7"/>
            <rect x="53" y="76" width="14" height="17" rx="5" fill="#E8B98F"/>
            <ellipse cx="60" cy="52" rx="22" ry="26" fill="#F2C9A5"/>
            <path d="M37 52c-4-24 12-32 25-31 17 1 24 14 21 31-5-12-15-16-27-15-9 1-15 6-19 15z" fill="#4A3FB0"/>
            <path d="M47 46q5-3 10 0M64 44q5-3 10 0" stroke="#2A2166" strokeWidth="2" strokeLinecap="round"/>
            <circle cx="54" cy="52" r="2.6" fill="#120F2E"/>
            <circle cx="71" cy="50" r="2.6" fill="#120F2E"/>
            <path d="M55 66q5-2 9 0" stroke="#9A5B4A" strokeWidth="2" strokeLinecap="round"/>
            <path d="M92 126 84 98 70 76" stroke="#6C5CE7" strokeWidth="14" strokeLinecap="round" strokeLinejoin="round"/>
            <circle cx="68" cy="72" r="8" fill="#F2C9A5"/>
          </svg>
          <div className="cg-hero-bubble">
            <b>Thinking<span className="cg-dot-ellipsis">...</span></b>
            Don't just get the answer. Understand it.
          </div>
        </div>
      </section>

      <section className="cg-dash-card cg-week-card cg-dash-span-4">
        <div className="cg-card-heading">
          <h2>This week</h2><Clock3 size={17}/>
        </div>
        <div className="cg-week-summary">
          <div className="cg-week-flame"><CalendarDays size={19}/></div>
          <div>
            <strong>{loading?'…':`${activeDays} day${activeDays===1?'':'s'}`}</strong>
            <span>with completed study sessions</span>
          </div>
        </div>
        <div className="cg-week-bars">
          {daily.map(day=><div className={`cg-week-day ${day.completed?'is-done':''} ${day.isToday?'is-today':''}`} key={day.iso}>
            <div className="cg-week-bar-space">
              <i style={{'--cg-height':`${day.height}%`} as React.CSSProperties}/>
            </div>
            <span>{day.label.slice(0,1)}</span>
          </div>)}
        </div>
        <div className="cg-week-foot">
          {plan
            ?`${completedSessions} of ${sessions.length} planned sessions completed`
            :'No saved study plan found for this week.'}
          <button onClick={()=>setPage('schedule')}>View schedule <ArrowUpRight size={13}/></button>
        </div>
      </section>

      <article className="cg-dash-card cg-stat cg-stat-violet cg-dash-span-3">
        <div className="cg-stat-icon"><MessageCircle size={19}/></div>
        <div className="cg-stat-number">{loading?'…':(data?.questions??0)}</div>
        <div className="cg-stat-label">Questions asked</div>
        <div className="cg-stat-sub">Across your conversations</div>
      </article>

      <article className="cg-dash-card cg-stat cg-stat-teal cg-dash-span-3">
        <div className="cg-stat-icon"><FolderOpen size={19}/></div>
        <div className="cg-stat-number">{loading?'…':(data?.sources??0)}</div>
        <div className="cg-stat-label">Course PDFs</div>
        <div className="cg-stat-sub">Materials available to your tutor</div>
      </article>

      <article className="cg-dash-card cg-stat cg-stat-amber cg-dash-span-3">
        <div className="cg-stat-icon"><Bookmark size={19}/></div>
        <div className="cg-stat-number">{loading?'…':(data?.visuals??0)}</div>
        <div className="cg-stat-label">Saved visuals</div>
        <button className="cg-stat-action" onClick={()=>setPage('saved')}>
          <Plus size={13}/> View visual library
        </button>
      </article>

      <article className="cg-dash-card cg-stat cg-stat-coral cg-dash-span-3">
        <div className="cg-stat-top">
          <div className="cg-stat-icon"><Target size={19}/></div>
          <svg className="cg-accuracy-ring" viewBox="0 0 62 62" aria-hidden="true">
            <circle className="cg-ring-track" cx="31" cy="31" r="25"/>
            <circle className="cg-ring-value" cx="31" cy="31" r="25"
              style={{'--cg-ring-offset':`${157-(157*Math.max(0,Math.min(100,Math.round((data?.quiz?.accuracy||0)*100)))/100)}`} as React.CSSProperties}/>
          </svg>
        </div>
        <div className="cg-stat-number">{loading?'…':`${Math.round((data?.quiz?.accuracy||0)*100)}%`}</div>
        <div className="cg-stat-label">Quiz accuracy</div>
        <div className="cg-stat-sub">{data?.quiz?.attempts||0} recorded attempts</div>
      </article>

      <section className="cg-dash-card cg-jump-card cg-dash-span-7">
        <div className="cg-card-heading"><h2>Jump back in</h2><Sparkles size={17}/></div>
        <div className="cg-jump-tiles">
          <button className="cg-jump-tile cg-jump-violet" onClick={()=>setPage('tutor')}>
            <span><MessageCircle size={18}/></span>
            <b>Ask the tutor <ArrowUpRight size={15}/></b>
          </button>
          <button className="cg-jump-tile cg-jump-teal" onClick={()=>setPage('quiz')}>
            <span><CircleHelp size={18}/></span>
            <b>Take a quiz <ArrowUpRight size={15}/></b>
          </button>
          <button className="cg-jump-tile cg-jump-orange" onClick={()=>setPage('revision')}>
            <span><BookOpen size={18}/></span>
            <b>Revise <ArrowUpRight size={15}/></b>
          </button>
        </div>
      </section>

      <section className="cg-dash-card cg-weak-card cg-dash-span-5">
        <div className="cg-card-heading">
          <h2>Needs attention</h2><Target size={17} className="cg-coral-icon"/>
        </div>
        {weakTopics.length
          ?weakTopics.map((topic:any)=><div className="cg-weak-topic" key={topic.topic}>
            <div className="cg-weak-label">
              <span>{topic.topic}</span>
              <b>{Math.round((topic.accuracy||0)*100)}%</b>
            </div>
            <div className="cg-weak-track">
              <i style={{
                '--cg-width':`${Math.max(0,Math.min(100,Math.round((topic.accuracy||0)*100)))}%`,
                '--cg-topic-color':(topic.accuracy||0)<.45?'#F4647B':(topic.accuracy||0)<.65?'#F5A524':'#2DD4BF'
              } as React.CSSProperties}/>
            </div>
          </div>)
          :<div className="cg-dash-empty">
            {loading?'Loading weak-topic data…':'No weak topics recorded yet.'}
            <span>Complete a quiz to discover topics to revisit.</span>
          </div>}
        <button className="cg-text-link" onClick={()=>setPage('weak')}>Explore weak topics <ArrowUpRight size={13}/></button>
      </section>

      <section className="cg-dash-card cg-recent-card cg-dash-span-7">
        <div className="cg-card-heading">
          <h2>Recent activity</h2><Clock3 size={17}/>
        </div>
        {recent.length
          ?recent.map((item:any,index:number)=><div className="cg-activity-row" key={`${item.event_type||'event'}-${item.created_at||index}-${index}`}>
            <div className={`cg-activity-icon cg-activity-${index%4}`}>
              <ActivityIcon event={item.event_type}/>
            </div>
            <div className="cg-activity-copy">
              <b>{String(item.event_type||'Activity').replace(/_/g,' ')}</b>
              <span>{item.detail||'Workspace activity'}</span>
            </div>
            <time>{timeAgo(item.created_at)}</time>
          </div>)
          :<div className="cg-dash-empty">
            {loading?'Loading activity…':'Your learning activity will appear here.'}
            <span>Ask your first question or complete a quiz to start building your history.</span>
          </div>}
      </section>

      <section className="cg-dash-card cg-reminder-card cg-dash-span-5">
        <div className="cg-reminder-icon"><MessageCircle size={19}/></div>
        <div>
          <div className="cg-reminder-kicker">STUDY REMINDERS</div>
          {reminders?.enabled
            ?<>
              <h2>Preferred time<br/>{reminderTime(reminders.reminder_time)}</h2>
              <p>Your reminder preference is saved.</p>
            </>
            :<>
              <h2>Plan your next<br/>study reminder</h2>
              <p>Choose a WhatsApp number and preferred time for study reminders.</p>
            </>}
          <div className="cg-dry-run-note">
            Delivery is currently in dry-run mode. No WhatsApp messages are being sent.
          </div>
        </div>
        <button className="cg-reminder-button" onClick={()=>setPage('reminders')}>
          {reminders?.enabled?'Edit reminders':'Set up reminders'}
          <ArrowUpRight size={14}/>
        </button>
      </section>
    </div>
    {loadError&&<div className="cg-dashboard-error" role="status">
      Dashboard data could not be fully loaded: {loadError}. Other sections may still be available.
    </div>}
  </div>;
}
function ActionRow({icon:Icon,title,desc,onClick,color}:any){return <button className="action-row" onClick={onClick}><div className={`action-icon ${color}`}><Icon size={18}/></div><div className="action-copy"><b>{title}</b><small>{desc}</small></div><ChevronRight size={17}/></button>}
function Empty({icon:Icon,title,text}:any){return <div className="empty"><div className="empty-icon"><Icon size={23}/></div><b>{title}</b><p>{text}</p></div>}
function plainReactText(value:any):string{if(value==null||typeof value==='boolean')return '';if(typeof value==='string'||typeof value==='number')return String(value);if(Array.isArray(value))return value.map(plainReactText).join('');if(React.isValidElement(value))return plainReactText((value.props as any).children);return ''}
function prepareTutorMarkdown(content:any,sources:any[]=[]):string{let text=String(content??'');text=text.replace(/\\\((.*?)\\\)/gs,(_m,formula)=>`$${formula}$`);text=text.replace(/\\\[([\s\S]*?)\\\]/g,(_m,formula)=>`$$\n${formula}\n$$`);text=text.replace(/\((\\(?:nabla|frac|sum|int|partial|sqrt|alpha|beta|gamma|delta|theta|lambda|mu|sigma|omega|cdot|times|log|exp|mathrm|mathbb|mathbf|operatorname)\b[^\n]{1,140})\)/g,(_m,formula)=>`$${formula.trim()}$`);const count=Array.isArray(sources)?sources.length:0;const normName=(value:any)=>String(value??'').trim().replace(/^['\"`]+|['\"`]+$/g,'').replace(/^.*[\\/]/,'').toLowerCase();text=text.replace(/\[([^\]\n,]{1,180})\s*,\s*p(?:age)?\.?\s*(\d+)\]/gi,(match,fileName,page)=>{const key=normName(fileName);const index=sources.findIndex((s:any)=>normName(s.source)===key&&String(s.page)===String(page));return index>=0?`[${index+1}](#cg-source-${index+1})`:match});text=text.replace(/(^|[^\w!])\[(\d{1,2})\](?!\s*\()/gm,(match,prefix,digits)=>{const n=Number(digits);return n>=1&&n<=count?`${prefix}[${n}](#cg-source-${n})`:match});text=text.replace(/【(\d{1,2})】/g,(match,digits)=>{const n=Number(digits);return n>=1&&n<=count?`[${n}](#cg-source-${n})`:match});return text}
function TutorEmptyState({onAsk}:any){const questions=['Why does gradient descent move opposite to the gradient?','How does logistic regression make a prediction?','What makes RAG answers grounded in a PDF?','How do neural-network layers learn?'];const [lineIndex,setLineIndex]=useState(0);const [typed,setTyped]=useState('');useEffect(()=>{let pos=0;let timer:number;setTyped('');const step=()=>{const target=questions[lineIndex];pos+=1;setTyped(target.slice(0,pos));if(pos<target.length)timer=window.setTimeout(step,34);else timer=window.setTimeout(()=>setLineIndex(i=>(i+1)%questions.length),1750)};timer=window.setTimeout(step,550);return()=>window.clearTimeout(timer)},[lineIndex]);const suggestions=[{text:'Why does gradient descent move opposite to the gradient?',Icon:Lightbulb,tone:'amber'},{text:'Help me understand logistic regression',Icon:Target,tone:'teal'},{text:'How does RAG work in CogniGraph?',Icon:FileText,tone:'violet'},{text:'Show me a diagram of a neural network',Icon:Workflow,tone:'coral'}];return <div className="cg-welcome"><div className="cg-thinking-row"><svg className="cg-thinking-person" viewBox="0 0 120 132" fill="none" role="img" aria-label="A student thinking"><path d="M12 132C12 102 34 90 60 90s48 12 48 42z" fill="#6C5CE7"/><rect x="53" y="76" width="14" height="17" rx="5" fill="#E8B98F"/><ellipse cx="60" cy="52" rx="22" ry="26" fill="#F2C9A5"/><path d="M37 52c-4-24 12-32 25-31 17 1 24 14 21 31-5-12-15-16-27-15-9 1-15 6-19 15z" fill="#4A3FB0"/><path d="M47 46q5-3 10 0M64 44q5-3 10 0" stroke="#2A2166" strokeWidth="2" strokeLinecap="round"/><circle cx="54" cy="52" r="2.6" fill="#120F2E"/><circle cx="71" cy="50" r="2.6" fill="#120F2E"/><path d="M55 66q5-2 9 0" stroke="#9A5B4A" strokeWidth="2" strokeLinecap="round"/><path d="M92 126 84 98 70 76" stroke="#6C5CE7" strokeWidth="14" strokeLinecap="round" strokeLinejoin="round"/><circle cx="68" cy="72" r="8" fill="#F2C9A5"/></svg><div className="cg-thought-bubble"><b>Thinking…</b><span>{typed||'Getting a question ready…'}<i aria-hidden="true"/></span></div></div><div className="cg-welcome-copy"><span className="cg-eyebrow">LET'S THINK IT THROUGH</span><h2>What are you trying to understand?</h2><p>Pick a starting point. CogniGraph will guide you step by step using your course material when it is relevant.</p></div><div className="cg-suggestion-grid">{suggestions.map((item:any)=><button key={item.text} type="button" className={`cg-suggestion ${item.tone}`} onClick={()=>onAsk(item.text)}><span className="cg-suggestion-icon"><item.Icon size={17}/></span><span>{item.text}</span><ArrowUpRight size={15} className="cg-suggestion-arrow"/></button>)}</div></div>}
function Tutor({token,courseId,notify}:any){const [chats,setChats]=useState<any[]>([]);const [cid,setCid]=useState<number|null>(null);const [messages,setMessages]=useState<any[]>([]);const [input,setInput]=useState('');const [busy,setBusy]=useState(false);const [err,setErr]=useState('');const [activeAnswer,setActiveAnswer]=useState<any>(null);const [sources,setSources]=useState<any[]>([]);const [sideTab,setSideTab]=useState('sources');const [search,setSearch]=useState('');const [uploadedSources,setUploadedSources]=useState<any[]>([]);const [deletingChat,setDeletingChat]=useState<number|null>(null);const [activeSource,setActiveSource]=useState<any>(null);const [railOpen,setRailOpen]=useState(false);const [helpful,setHelpful]=useState<Record<string,boolean>>({});const [chatMode,setChatMode]=useState<'socratic'|'normal'>('socratic');
const loadChats=()=>request(courseId?`/api/courses/${courseId}/chats`:'/api/chats',token).then(setChats).catch(e=>setErr(e.message));useEffect(()=>{setCid(null);setMessages([]);setSources([]);setActiveAnswer(null);setActiveSource(null);setHelpful({});setChatMode('socratic');setRailOpen(false);loadChats();if(courseId){request(`/api/courses/${courseId}/sources`,token).then((rows:any[])=>setUploadedSources(rows||[])).catch(()=>setUploadedSources([]))}else{setUploadedSources([])}},[courseId,token]);useEffect(()=>{if(!cid)return;let cancelled=false;setMessages([]);setSources([]);setActiveAnswer(null);setActiveSource(null);setHelpful({});setErr('');request(`/api/chats/${cid}/messages`,token).then((rows:any[])=>{if(cancelled)return;const loaded=(rows||[]).map((m:any)=>({...m,sources:(()=>{try{const raw=JSON.parse(m.context_json||'[]');return Array.isArray(raw)?raw:[]}catch{return []}})()}));setMessages(loaded);const lastAssistant=[...loaded].reverse().find((m:any)=>m.role==='assistant');const lastUser=[...loaded].reverse().find((m:any)=>m.role==='user');setSources(lastAssistant?.sources||[]);setActiveAnswer(lastAssistant&&lastUser?{query:lastUser.content,response:lastAssistant.content,conversation_id:cid}:null)}).catch((e:any)=>{if(!cancelled)setErr(e.message)});return()=>{cancelled=true}},[cid,token]);
async function deleteChat(event:any,chat:any){
event.stopPropagation();
if(!window.confirm(`Delete "${chat.title}" and all its messages? This cannot be undone.`))return;
setDeletingChat(chat.id);setErr('');
try{
await request(`/api/chats/${chat.id}`,token,{method:'DELETE'});
setChats((rows:any[])=>rows.filter(c=>c.id!==chat.id));
if(cid===chat.id){setCid(null);setMessages([]);setActiveAnswer(null);setSources([]);setActiveSource(null);setHelpful({});setRailOpen(false)}
notify('Conversation deleted');
}catch(e:any){setErr(e.message)}
finally{setDeletingChat(null)}
}
async function send(text=input){if(!text.trim()||busy)return;setBusy(true);setErr('');const last=messages[messages.length-1];const retrying=!!last&&last.role==='user'&&last.failed===true&&last.content===text;const userMsg=retrying?last:{role:'user',content:text,failed:false};if(!retrying)setMessages(m=>[...m,userMsg]);setInput('');try{const d=await request('/api/chat',token,{method:'POST',body:JSON.stringify({course_id:courseId,conversation_id:cid,message:text,chat_mode:chatMode})});setCid(d.conversation_id);setMessages(m=>[...m.filter((x:any)=>x!==userMsg),{...userMsg,failed:false},{role:'assistant',content:d.answer,mode:d.mode,sources:d.sources,visualization:d.visualization,elapsed_seconds:d.elapsed_seconds}]);setSources(d.sources||[]);setActiveAnswer({query:text,response:d.answer,conversation_id:d.conversation_id});loadChats()}catch(e:any){setErr(e.message);setInput(text);setMessages(m=>m.map((x:any)=>x===userMsg?{...x,failed:true}:x))}finally{setBusy(false)}}
async function action(kind:'explain'|'visualize', target:any=activeAnswer){if(!target)return;setBusy(true);try{const d=await request(`/api/actions/${kind}`,token,{method:'POST',body:JSON.stringify({course_id:courseId,conversation_id:cid,query:target.query,original_response:target.response})});setMessages(m=>[...m,{role:'assistant',content:kind==='explain'?d.answer:`Generated ${String(d.kind||'visualization').replace('_',' ')} for: ${target.query}`,visualization:kind==='visualize'?d:null,sources:d.sources||[]}]);notify(kind==='explain'?'Simpler explanation ready':'Visualization generated')}catch(e:any){setErr(e.message)}finally{setBusy(false)}}
return <div className="tutor-layout cg-tutor-redesign"><section className="chat-column"><div className="tutor-top"><div className="tutor-identity"><div className="tutor-mark"><BrainCircuit size={23}/></div><div><h2>{chatMode==='normal'?'Normal Chat':'Socratic Tutor'}</h2><p><span className="status-dot"/>{courseId?(chatMode==='normal'?'General chat · course sources ignored':'Course-grounded learning'):(chatMode==='normal'?'General AI assistant':'Socratic guidance · no course needed')}</p></div></div><div className="tutor-head-actions">{!cid&&!messages.length&&<div className="cg-mode-switch" role="group" aria-label="Choose chat mode"><button type="button" className={chatMode==='socratic'?'selected':''} onClick={()=>setChatMode('socratic')}><BrainCircuit size={15}/><span>Socratic</span></button><button type="button" className={chatMode==='normal'?'selected':''} onClick={()=>setChatMode('normal')}><MessageCircle size={15}/><span>Normal Chat</span></button></div>}<button className="secondary small tutor-mobile-sources" onClick={()=>{setSideTab('sources');setRailOpen(true)}}><FileText size={15}/> Sources</button><button className="secondary small" onClick={()=>{setCid(null);setMessages([]);setActiveAnswer(null);setSources([]);setActiveSource(null);setHelpful({});setErr('');setSideTab('sources');setRailOpen(false)}}><Plus size={15}/> New chat</button></div></div><div className="chat-workspace">{!messages.length?<TutorEmptyState onAsk={send}/>:<div className="messages">{messages.map((m:any,i:number)=><div className={`message ${m.role}`} key={i}><div className={`message-avatar ${m.role}`}>{m.role==='assistant'?<BrainCircuit size={17}/>:<GraduationCap size={17}/>}</div><div className="message-body"><div className="message-label">{m.role==='assistant'?<><span className="cg-message-brand"><span className="cg-mini-mark"><BrainCircuit size={13}/></span>{chatMode==='normal'?'COGNIGRAPH CHAT':'COGNIGRAPH TUTOR'}</span>{m.sources?.length>0&&<span className="cg-course-tag">From your course</span>}</>:'YOU'}{m.elapsed_seconds&&<span className="cg-elapsed"> · {m.elapsed_seconds}s</span>}</div><div className="message-content"><ReactMarkdown remarkPlugins={[remarkGfm,remarkMath]} rehypePlugins={[rehypeKatex]} components={{pre:({children}:any)=><TutorCodeBlock>{children}</TutorCodeBlock>,a:({href,children,...props}:any)=>{if(href?.startsWith('#cg-source-')){const n=Number(href.slice('#cg-source-'.length));const cited=m.sources?.[n-1];return <button type="button" className="cg-inline-citation" onClick={()=>{if(cited){setActiveSource(cited);setSources(m.sources||[]);setSideTab('sources');setRailOpen(true)}}}>{children}</button>}return <a href={href} {...props}>{children}</a>},p:({children,...props}:any)=>{const question=plainReactText(children).trim().endsWith('?');return question?<div className="cg-your-turn"><div className="cg-your-turn-label">Your turn</div><p {...props}>{children}</p></div>:<p {...props}>{children}</p>},blockquote:({children}:any)=><blockquote className="cg-amber-callout">{children}</blockquote>}}>{prepareTutorMarkdown(m.content,m.sources)}</ReactMarkdown></div>{Array.isArray(m.sources)&&m.sources.length>0&&<div className="cg-answer-sources"><div className="cg-sources-title">Where this came from</div><div className="cg-source-strip">{m.sources.map((s:any,j:number)=><button type="button" className={`cg-source-card edge-${j%4} ${activeSource?.source===s.source&&String(activeSource?.page)===String(s.page)?'selected':''}`} key={`${s.source||'source'}-${s.page??'na'}-${j}`} onClick={()=>{setActiveSource(s);setSources(m.sources||[]);setSideTab('sources');setRailOpen(true)}}><span className="cg-source-num">{j+1}</span><span className="cg-source-meta"><b>{s.source||'Course material'}</b><small>Page {s.page??'—'}{s.similarity!=null&&Number.isFinite(Number(s.similarity))?` · ${Math.round(Number(s.similarity)*100)}% match`:''}</small></span></button>)}</div></div>}{m.visualization&&<VisualResult data={m.visualization} onSave={()=>request('/api/visualizations',token,{method:'POST',body:JSON.stringify({course_id:courseId,kind:m.visualization.kind||'diagram',title:`${m.visualization.kind||'Visualization'}: ${m.content.slice(0,45)}`,query:m.content,source_text:m.visualization.mermaid||'',image_base64:m.visualization.image||''})}).then(()=>notify('Saved to your visual library')).catch((e:any)=>setErr(e.message))}/>}{m.role==='assistant'&&!m.visualization&&i===messages.length-1&&courseId&&chatMode==='socratic'&&<div className="answer-actions"><button onClick={()=>{setActiveAnswer({query:messages.filter((x:any)=>x.role==='user').slice(-1)[0]?.content||'',response:m.content});action('explain',{query:messages.filter((x:any)=>x.role==='user').slice(-1)[0]?.content||'',response:m.content})}}><Lightbulb size={14}/> Explain simply</button><button onClick={()=>{setActiveAnswer({query:messages.filter((x:any)=>x.role==='user').slice(-1)[0]?.content||'',response:m.content});action('visualize',{query:messages.filter((x:any)=>x.role==='user').slice(-1)[0]?.content||'',response:m.content})}}><Workflow size={14}/> Visualize</button><button className={helpful[String(i)]?'is-thanked':''} onClick={()=>setHelpful((prev:any)=>({...prev,[String(i)]:true}))}><CheckCircle2 size={14}/>{helpful[String(i)]?'Thanks!':'Helpful'}</button></div>}</div></div>)}{busy&&<div className="thinking"><div className="message-avatar assistant"><BrainCircuit size={17}/></div><div><div className="message-label">COGNIGRAPH IS THINKING</div><div className="thinking-dots"><i/><i/><i/></div><small>{chatMode==='normal'?'Preparing a direct answer…':courseId?'Retrieving course context and preparing guidance…':'Thinking through the question…'}</small></div></div>}{err&&<div className="alert error">{err}</div>}</div>}</div><div className="composer-wrap"><div className="composer"><textarea value={input} onChange={e=>setInput(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send()}}} placeholder={courseId&&chatMode==='socratic'?"Ask a question about your course…":chatMode==='normal'?"Ask anything…":"What would you like to learn?"} rows={1}/><button className="send-button" disabled={!input.trim()||busy} onClick={()=>send()}><Send size={17}/></button></div><div className="composer-foot"><span><ShieldCheck size={13}/> Answers are grounded in your course sources when available</span><span>Enter to send · Shift + Enter for new line</span></div></div></section><button type="button" className={`cg-rail-backdrop ${railOpen?'is-open':''}`} onClick={()=>setRailOpen(false)} aria-label="Close sources and history panel"/><aside className={`tutor-rail ${railOpen?'is-open':''}`}><div className="tutor-rail-top"><div className="rail-tabs"><button className={sideTab==='sources'?'selected':''} onClick={()=>setSideTab('sources')}>Sources</button><button className={sideTab==='history'?'selected':''} onClick={()=>setSideTab('history')}>History</button></div><button type="button" className="tutor-rail-close" onClick={()=>setRailOpen(false)} aria-label="Close panel">×</button></div><div className="tutor-rail-content">{sideTab==='sources'?<>{uploadedSources.length>0&&<><div className="rail-heading"><h3>Uploaded course PDFs</h3><span className="count-badge">{uploadedSources.length}</span></div><p className="rail-description cg-index-summary">{uploadedSources.reduce((sum:number,s:any)=>sum+(Number(s.chunks)||0),0).toLocaleString()} indexed chunks across {uploadedSources.length} PDF{uploadedSources.length===1?'':'s'} in this course.</p>{uploadedSources.map((s:any)=><div className="source-card" key={s.id}><div className="source-file"><FileText size={16}/></div><div><b>{s.filename}</b><small>{s.chunks} chunks indexed</small></div></div>)}</>}<div className="rail-heading"><h3>Course context</h3><span className="count-badge">{sources.length}</span></div><p className="rail-description">Click a numbered citation or page card to highlight the matching retrieval result. Relevance is the retriever score, not a guaranteed probability.</p>{sources.length?sources.map((s:any,i:number)=><button type="button" className={`source-card cg-page-source edge-${i%4} ${activeSource?.source===s.source&&String(activeSource?.page)===String(s.page)?'is-active':''}`} key={`${s.source||'source'}-${s.page??'na'}-${i}`} onClick={()=>setActiveSource(s)}><div className="source-file"><FileText size={16}/></div><div><b>{s.source||'Course material'}</b><small>Page {s.page??'—'} · relevance {s.similarity!=null&&Number.isFinite(Number(s.similarity))?`${Math.round(Number(s.similarity)*100)}%`: 'score unavailable'}</small></div>{activeSource?.source===s.source&&String(activeSource?.page)===String(s.page)&&<CheckCircle2 size={15}/>}</button>):<Empty icon={FileText} title="No answer sources yet" text={uploadedSources.length?"Your PDFs are indexed. Ask a question about their contents to see cited passages here.":"Upload a course PDF in Course Workspace, then ask a related question."}/>}<div className="rail-tip"><Lightbulb size={17}/><div><b>Try Socratic learning</b><p>Explain your reasoning and the tutor will help you examine it step by step.</p></div></div></>:<>{chats.filter((c:any)=>String(c.title||'Untitled chat').toLowerCase().includes(search.trim().toLowerCase())).map((c:any)=><div className={`history-row ${cid===c.id?'chosen':''}`} key={c.id}><button className={`history-item ${cid===c.id?'chosen':''}`} onClick={()=>{setChatMode(c.chat_mode==='normal'?'normal':'socratic');setCid(c.id);setRailOpen(false)}} title={c.title||'Untitled chat'}><MessageCircle size={15}/><span><b>{c.title||'Untitled chat'}</b><small>{c.updated_at?new Date(Number(c.updated_at)*1000).toLocaleDateString():'Conversation'}</small></span></button><button className="history-delete" title={`Delete ${c.title||'conversation'}`} aria-label={`Delete ${c.title||'conversation'}`} disabled={deletingChat===c.id} onClick={e=>deleteChat(e,c)}><Trash2 size={14}/></button></div>)}{!chats.length&&<div className="cg-history-empty"><MessageCircle size={20}/><b>No conversations yet</b><p>Your saved chats will appear here after your first question.</p></div>}{chats.length>0&&!chats.some((c:any)=>String(c.title||'Untitled chat').toLowerCase().includes(search.trim().toLowerCase()))&&<div className="cg-history-empty"><Search size={20}/><b>No matches found</b><p>Try another word from the chat title.</p></div>}<input className="search-field" value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search chats"/></>}</div></aside></div>}
function MermaidDiagram({source}:{source:string}){const [svg,setSvg]=useState('');const [err,setErr]=useState('');useEffect(()=>{let alive=true;mermaid.initialize({
  startOnLoad: false,
  theme: 'base',
  securityLevel: 'strict',
  themeVariables: {
    background: '#100D2D',
    primaryColor: '#29214F',
    primaryTextColor: '#F5F3FF',
    primaryBorderColor: '#9B8CFF',
    lineColor: '#B4A7FF',
    secondaryColor: '#123B43',
    secondaryTextColor: '#F5F3FF',
    tertiaryColor: '#3A2D65',
    tertiaryTextColor: '#F5F3FF',
    edgeLabelBackground: '#17133C',
    fontFamily: 'Inter, ui-sans-serif, sans-serif',
    fontSize: '16px'
  },
  flowchart: {
    useMaxWidth: false,
    nodeSpacing: 50,
    rankSpacing: 60,
    curve: 'basis'
  }
});mermaid.render(`cg-${Math.random().toString(36).slice(2)}`,source).then(r=>{if(alive)setSvg(r.svg)}).catch(()=>{if(alive)setErr('Diagram could not be rendered; source is available below.')});return()=>{alive=false}},[source]);return <div>{svg?<div className="mermaid-svg" dangerouslySetInnerHTML={{__html:svg}}/>:err?<p>{err}</p>:<p className="muted">Rendering diagram…</p>}<details><summary>Diagram source</summary><pre>{source}</pre></details></div>}
function VisualResult({data,onSave}:any){if(!data)return null;return <div className="visual-result">{data.image?<img src={`data:image/png;base64,${data.image}`} alt="Generated course visualization"/>:data.mermaid?<MermaidDiagram source={data.mermaid}/>:<><b>{data.kind||'Visualization'}</b><p>{data.message||'Visualization result is ready.'}</p></>}{onSave&&<button className="secondary small" onClick={onSave}><Bookmark size={14}/> Save to library</button>}</div>}
function Quiz({token,courseId,notify,initialTopic='',practiceWeakTopics=false}:any){
const [topic,setTopic]=useState(String(initialTopic||''));
const [q,setQ]=useState<any>(null);
const [selected,setSelected]=useState<number|null>(null);
const [hint,setHint]=useState(0);
const [result,setResult]=useState<any>(null);
const [stats,setStats]=useState<any>(null);
const [loading,setLoading]=useState(false);
const [number,setNumber]=useState(1);
const [questionCount,setQuestionCount]=useState(5);
const [err,setErr]=useState('');
const [courseSources,setCourseSources]=useState<any[]>([]);
const [weakTopics,setWeakTopics]=useState<any[]>([]);
 const [weakTopicsLoaded,setWeakTopicsLoaded]=useState(false);
const [sessionCorrect,setSessionCorrect]=useState(0);
const [thoughtText,setThoughtText]=useState('');

useEffect(()=>{
  let cancelled=false;
  setCourseSources([]);setWeakTopics([]);setStats(null);setWeakTopicsLoaded(false);
  if(!courseId)return ()=>{cancelled=true};
  request(`/api/courses/${courseId}/sources`,token).then((rows:any[])=>{
    if(!cancelled)setCourseSources(Array.isArray(rows)?rows:[]);
  }).catch(()=>{if(!cancelled)setCourseSources([])});
  request(`/api/courses/${courseId}/dashboard`,token).then((d:any)=>{
    if(!cancelled)setStats(d?.quiz??null);
  }).catch(()=>{if(!cancelled)setStats(null)});
  request(`/api/courses/${courseId}/weak-topics`,token).then((d:any)=>{
    if(cancelled)return;
    setWeakTopics(Array.isArray(d?.topics)?d.topics.filter((t:any)=>typeof t?.topic==='string'&&t.topic.trim()):[]);
    if(d?.stats)setStats((previous:any)=>previous??d.stats);
  }).catch(()=>{if(!cancelled)setWeakTopics([])}).finally(()=>{if(!cancelled)setWeakTopicsLoaded(true)});
  return ()=>{cancelled=true};
},[courseId,token]);

  useEffect(()=>{
    if(!practiceWeakTopics||!weakTopicsLoaded||!weakTopics.length||q||result||loading)return;
    setQuestionCount(5);
    setTopic('');
    void loadQuestion(true,1,String(weakTopics[0].topic));
  },[practiceWeakTopics,weakTopicsLoaded,weakTopics.length,courseId,token]);

useEffect(()=>{
  const prompts=[
    'What does the learning rate control in gradient descent?',
    'Why can a model perform well on training data but poorly on new data?',
    'How can you tell whether an answer is supported by your course PDF?'
  ];
  let cancelled=false;
  let timer:number|undefined;
  if(typeof window!=='undefined'&&window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)').matches){setThoughtText(prompts[0]);return;}
  let promptIndex=0;
  const showNext=()=>{
    const line=prompts[promptIndex];let position=0;setThoughtText('');
    const type=()=>{
      if(cancelled)return;
      position+=1;setThoughtText(line.slice(0,position));
      if(position<line.length)timer=window.setTimeout(type,29);
      else timer=window.setTimeout(()=>{promptIndex=(promptIndex+1)%prompts.length;showNext()},2300);
    };
    timer=window.setTimeout(type,500);
  };
  showNext();
  return ()=>{cancelled=true;if(timer!==undefined)window.clearTimeout(timer)};
},[]);

const chunkCount=courseSources.reduce((total:number,s:any)=>total+Math.max(0,Number(s?.chunks)||0),0);
const attemptCount=Number(stats?.attempts)||0;
const correctCount=Number(stats?.correct)||0;
const accuracy=attemptCount>0&&Number.isFinite(Number(stats?.accuracy))?Math.round(Number(stats.accuracy)*100):null;
const topicSuggestions=weakTopics.map((t:any)=>String(t.topic).trim()).filter(Boolean).filter((v:string,i:number,a:string[])=>a.indexOf(v)===i).slice(0,practiceWeakTopics?12:4);
const hints=Array.isArray(q?.hints)?q.hints.filter((item:any)=>typeof item==='string'&&item.trim()):[];
const correctIndex=Number.isInteger(result?.correct_index)?Number(result.correct_index):(result?.correct_answer&&Array.isArray(q?.options)?q.options.findIndex((o:any)=>String(o)===String(result.correct_answer)):-1);

async function loadQuestion(newSession:boolean,targetNumber:number,requestTopic=topic){
  if(!courseId){setErr('Select a course before starting a quiz.');return;}
  if(loading)return;
  setLoading(true);setErr('');
  if(newSession){setQ(null);setResult(null);setSelected(null);setHint(0);setSessionCorrect(0);setNumber(1);}
  try{
    const d=await request('/api/quiz/question',token,{method:'POST',body:JSON.stringify({course_id:courseId,topic:String(requestTopic??'').trim()})});
    const question=d?.question;
    const questionId=d?.question_id??question?.question_id??question?.id;
    if(!question||typeof question.question!=='string'||!question.question.trim()||!Array.isArray(question.options)||question.options.length<2){
      throw new Error('The quiz generator returned an incomplete question. No answer was submitted. Please try again.');
    }
    if(questionId===undefined||questionId===null||String(questionId).trim()===''){
      throw new Error('The quiz API did not return a question tracking ID. No answer was submitted; please try again or check the API version.');
    }
    const normalized={...question,options:question.options.map((o:any)=>String(o??'')),question_id:questionId};
    if(normalized.options.some((o:string)=>!o.trim()))throw new Error('The generated question contains an empty option. Please generate another question.');
    setQ(normalized);setNumber(targetNumber);setSelected(null);setHint(0);setResult(null);
    if(d?.stats)setStats(d.stats);
  }catch(e:any){
    setErr(e?.message||'Could not load a quiz question. Check your connection and try again.');
    // On a new session, show the setup state; during a next-question retry,
    // retain the already-answered question and result instead of losing progress.
    if(newSession){setQ(null);setResult(null);}
  }finally{setLoading(false)}
}

async function start(){const firstTopic=practiceWeakTopics&&!topic.trim()&&topicSuggestions.length?topicSuggestions[0]:topic;await loadQuestion(true,1,firstTopic);}
async function startQuick(){
  if(loading)return;
  if(q&&!result?.finished&&!window.confirm('Leave this quiz and start a new 5-question session? Answers already submitted remain in your saved quiz history.'))return;
  setQuestionCount(5);setTopic('');const firstTopic=practiceWeakTopics&&topicSuggestions.length?topicSuggestions[0]:'';await loadQuestion(true,1,firstTopic);
}
async function submit(){
  if(selected===null||!q||result||loading)return;
  setLoading(true);setErr('');
  try{
    const d=await request('/api/quiz/answer',token,{method:'POST',body:JSON.stringify({course_id:courseId,question_id:q.question_id,selected_index:selected,hints_used:hint})});
    if(!d||typeof d.correct!=='boolean')throw new Error('The API did not confirm whether this answer was recorded. Refresh your progress before trying to answer again.');
    setResult(d);if(d.stats)setStats(d.stats);if(d.correct)setSessionCorrect((current:number)=>current+1);
  }catch(e:any){setErr(e?.message||'Could not submit this answer. Check your connection and retry only after confirming whether the attempt was recorded.');}
  finally{setLoading(false)}
}
async function next(){
  if(loading||!result||result.finished)return;
  if(number>=questionCount){setQ(null);setResult({finished:true});return;}
  const nextTopic=practiceWeakTopics&&topicSuggestions.length?topicSuggestions[number%topicSuggestions.length]:topic;await loadQuestion(false,number+1,nextTopic);
}
function requestHint(){
  if(loading)return;
  const maxHints=Math.min(3,hints.length||1);
  setHint((current:number)=>Math.min(maxHints,current+1));
}

return <div className="cg-quiz-redesign">
  <section className="cgq-hero">
    <svg className="cgq-hero-bg" viewBox="0 0 900 220" preserveAspectRatio="xMidYMid slice" aria-hidden="true"><g stroke="#B8AFFF" strokeOpacity=".3" fill="none"><path d="M70 40 200 120 150 190M200 120 360 60 470 150 360 200M470 150 620 60M620 60 760 140 860 50"/></g><g><circle cx="70" cy="40" r="5" fill="#B8AFFF"/><circle cx="200" cy="120" r="7" fill="#5EEAD4"/><circle cx="360" cy="60" r="6" fill="#B8AFFF"/><circle cx="470" cy="150" r="8" fill="#FFC86B"/><circle cx="620" cy="60" r="5" fill="#5EEAD4"/><circle cx="760" cy="140" r="6" fill="#B8AFFF"/></g></svg>
    <div className="cgq-hero-copy"><span className="cgq-kicker">PRACTICE & FEEDBACK</span><h1>Test what you know.</h1><p>{courseSources.length?`Practice questions from your selected course material.`:'Upload course material to enable grounded practice.'} Your quiz history is saved as you answer.</p><button type="button" className="cgq-quick" onClick={startQuick} disabled={loading||(practiceWeakTopics&&!weakTopicsLoaded)}><span aria-hidden="true">▶</span>{loading?'Preparing quiz…':(practiceWeakTopics&&!weakTopicsLoaded)?'Loading weak topics…':'Quick 5-question quiz'}</button></div>
    <div className="cgq-thinker" aria-label="A thinking student"><svg className="cgq-person" viewBox="0 0 120 132" fill="none" role="img" aria-label="A student thinking"><path d="M12 132C12 102 34 90 60 90s48 12 48 42z" fill="#6C5CE7"/><rect x="53" y="76" width="14" height="17" rx="5" fill="#E8B98F"/><ellipse cx="60" cy="52" rx="22" ry="26" fill="#F2C9A5"/><path d="M37 52c-4-24 12-32 25-31 17 1 24 14 21 31-5-12-15-16-27-15-9 1-15 6-19 15z" fill="#4A3FB0"/><path d="M47 46q5-3 10 0M64 44q5-3 10 0" stroke="#2A2166" strokeWidth="2" strokeLinecap="round"/><circle cx="54" cy="52" r="2.6" fill="#120F2E"/><circle cx="71" cy="50" r="2.6" fill="#120F2E"/><path d="M55 66q5-2 9 0" stroke="#9A5B4A" strokeWidth="2" strokeLinecap="round"/><path d="M92 126 84 98 70 76" stroke="#6C5CE7" strokeWidth="14" strokeLinecap="round" strokeLinejoin="round"/><circle cx="68" cy="72" r="8" fill="#F2C9A5"/></svg><div className="cgq-thought"><b>Thinking<span className="cgq-dots" aria-hidden="true"><i/><i/><i/></span></b><p>{thoughtText||'Finding a good question…'}<i className="cgq-caret" aria-hidden="true"/></p></div></div>
  </section>

  <section className="cgq-stats" aria-label="Your saved quiz and course statistics">
    <article className="cgq-stat cgq-stat-pdfs"><span className="cgq-stat-icon"><FileText size={19}/></span><div><strong>{courseSources.length}</strong><b>Course PDF{courseSources.length===1?'':'s'}</b><small>{courseSources.length?'Indexed for this course':'No PDFs indexed yet'}</small><em>{chunkCount.toLocaleString()} chunks</em></div></article>
    <article className="cgq-stat cgq-stat-attempts"><span className="cgq-stat-icon"><CircleHelp size={19}/></span><div><strong>{stats?attemptCount:'—'}</strong><b>Attempts</b><small>{stats?(attemptCount===1?'Saved answer':'Saved answers'):'Progress unavailable'}</small></div></article>
    <article className="cgq-stat cgq-stat-correct"><span className="cgq-stat-icon"><CheckCircle2 size={19}/></span><div><strong>{stats?correctCount:'—'}</strong><b>Correct</b><small>{stats?'Across saved attempts':'Progress unavailable'}</small></div></article>
    <article className="cgq-stat cgq-stat-accuracy"><span className="cgq-stat-icon"><Target size={19}/></span><div><strong>{accuracy===null?'—':`${accuracy}%`}</strong><b>Accuracy</b><small>{attemptCount?`${attemptCount} saved attempt${attemptCount===1?'':'s'}`:stats?'No answers yet':'Progress unavailable'}</small></div></article>
  </section>

  <div className="cgq-main-grid">
    <section className="cgq-card cgq-practice">
      {!q&&!result?.finished&&<div className="cgq-setup">
        <div className="cgq-section-head"><span className="cgq-section-icon"><span aria-hidden="true">▶</span></span><div><h2>{practiceWeakTopics?'Practice your weak topics':'Start a practice session'}</h2><p>{practiceWeakTopics?'Questions rotate through your saved weak topics, one at a time.':'Choose the session length and optional topic.'}</p></div></div>
        <div className="cgq-label"><span aria-hidden="true">☷</span> How many questions?</div>
        <div className="cgq-segmented cgq-counts" role="group" aria-label="Number of questions">{[5,10,15,20].map((n:number)=><button key={n} type="button" aria-pressed={questionCount===n} onClick={()=>setQuestionCount(n)} disabled={loading}>{n}</button>)}</div>
        <label className="cgq-label" htmlFor="cgq-topic"><Search size={16}/> Topic <span className="cgq-optional">(optional)</span></label>
        <div className="cgq-topic-input"><Search size={17}/><input id="cgq-topic" value={topic} onChange={e=>setTopic(e.target.value)} placeholder={practiceWeakTopics?'Rotating through weak topics':'Any topic, or leave blank to auto-select'} disabled={loading||practiceWeakTopics}/></div>
        <div className="cgq-topic-suggestions">{topicSuggestions.length?topicSuggestions.map((name:string)=><button type="button" key={name} onClick={()=>setTopic(name)} disabled={loading}>{name}</button>):<span>Suggested review topics appear as quiz history grows. Leave the topic blank to let CogniGraph choose from the selected course.</span>}</div>
        <div className="cgq-label"><Sparkles size={15}/> Difficulty</div>
        <div className="cgq-adaptive-row"><span className="cgq-adaptive-pill"><Sparkles size={14}/> Adaptive</span><p>The quiz API chooses difficulty from your saved performance. Current question difficulty appears during the session.</p></div>
        {err&&<div role="alert" className="cgq-alert">{err}</div>}
        <button type="button" className="cgq-start" onClick={start} disabled={loading||!courseId||(practiceWeakTopics&&!weakTopicsLoaded)}>{loading?<><LoaderCircle size={17} className="cgq-spin"/> Preparing question…</>:(practiceWeakTopics&&!weakTopicsLoaded)?<>Loading weak topics…</>:<> <span aria-hidden="true">▶</span> Start {questionCount}-question quiz <ArrowUpRight size={17}/></>}</button>
        {!courseSources.length&&<p className="cgq-source-note">No course PDF is listed for this workspace yet. A source-grounded quiz may need an uploaded PDF. You can upload one in Course Workspace.</p>}
      </div>}

      {q&&!result?.finished&&<div className="cgq-question-state">
        <div className="cgq-question-top"><div><span className="cgq-kicker">PRACTICE SESSION</span><h2>{q.topic||topic||'Course topic'}</h2><p>{q.difficulty?`Difficulty: ${String(q.difficulty)}`:'Adaptive difficulty'}{hint?` · ${hint} hint${hint===1?'':'s'} used`:''}</p></div><button type="button" className="cgq-exit" title="Leave this quiz" aria-label="Leave this quiz" disabled={loading} onClick={()=>{if(window.confirm('Leave this quiz? Answers already submitted remain in your quiz history.')){setQ(null);setResult(null);setSelected(null);setHint(0);setNumber(1);setSessionCorrect(0);setErr('')}}}>×</button></div>
        <div className="cgq-progress-head"><span>Question {number} of {questionCount}</span><span>{Math.round(Math.min(number,questionCount)/questionCount*100)}% through</span></div><div className="cgq-progress"><span style={{width:`${Math.min(number,questionCount)/questionCount*100}%`}}/></div>
        <div className="cgq-question-text">{q.question}</div>
        <div className="cgq-options">{q.options.map((option:string,index:number)=><button key={`${index}-${option}`} type="button" disabled={!!result||loading} onClick={()=>setSelected(index)} aria-pressed={selected===index} className={`cgq-option ${selected===index?'is-selected':''} ${result&&index===correctIndex?'is-correct':''} ${result&&selected===index&&result.correct===false?'is-wrong':''}`}><span className="cgq-option-letter">{String.fromCharCode(65+index)}</span><span className="cgq-option-text">{option}</span>{result&&index===correctIndex&&<CheckCircle2 size={18} className="cgq-option-check"/>}</button>)}</div>
        {!result&&<div className="cgq-question-actions"><button type="button" className="cgq-hint-button" onClick={requestHint} disabled={loading||hint>=Math.min(3,hints.length||1)}><span><Lightbulb size={17}/></span> I’m stuck{hints.length?` · Hint ${hint}/${Math.min(3,hints.length)}`:hint?' · No generated hint':' · Hint'}</button><button type="button" className="cgq-submit" onClick={submit} disabled={selected===null||loading}>{loading?<><LoaderCircle size={16} className="cgq-spin"/> Checking…</>:<>Submit answer <ArrowUpRight size={16}/></>}</button></div>}
        {hint>0&&!result&&<div className="cgq-hint-box"><span className="cgq-hint-icon"><Lightbulb size={17}/></span><div><b>Hint {hint}</b><p>{hints.length?hints[Math.min(hint,hints.length)-1]:'This question did not include a generated hint. Review the key idea from your selected course material and eliminate options that do not fit.'}</p></div></div>}
        {result&&<div className={`cgq-feedback ${result.correct?'is-good':'is-bad'}`} role="status"><span className="cgq-feedback-icon">{result.correct?<CheckCircle2 size={20}/>:<CircleHelp size={20}/>}</span><div className="cgq-feedback-copy"><b>{result.correct?'Correct — well done':'Not quite. Let’s learn from it.'}</b><p>{result.explanation||'Your answer was recorded. Review the concept before continuing.'}</p>{correctIndex>=0&&<small>Correct option: {String.fromCharCode(65+correctIndex)}</small>}</div><button type="button" className="cgq-next" onClick={next} disabled={loading}>{loading?<><LoaderCircle size={15} className="cgq-spin"/> Loading…</>:number>=questionCount?'See results':err?'Retry next question':'Next question'} <ChevronRight size={16}/></button></div>}
        {err&&<div role="alert" className="cgq-alert">{err}</div>}
      </div>}

      {result?.finished&&<div className="cgq-finished"><div className="cgq-finish-mark"><CheckCircle2 size={30}/></div><span className="cgq-kicker">SESSION COMPLETE</span><h2>You kept going. That counts.</h2><p>Your answers have been sent to CogniGraph and saved quiz attempts update your progress.</p><div className="cgq-score-ring"><strong>{Math.round(sessionCorrect/questionCount*100)}%</strong><span>Session score</span></div><div className="cgq-session-summary"><div><b>{sessionCorrect} / {questionCount}</b><small>Correct in this session</small></div><div><b>{attemptCount}</b><small>Total saved attempts</small></div></div><button type="button" className="cgq-start" onClick={()=>loadQuestion(true,1,topic)} disabled={loading}>{loading?<><LoaderCircle size={17} className="cgq-spin"/> Preparing…</>:<><RefreshCw size={17}/> Practice again</>}</button><button type="button" className="cgq-text-button" onClick={()=>{setResult(null);setQ(null);setErr('');setNumber(1);setSessionCorrect(0)}}>Change topic or session length</button></div>}
    </section>

    <aside className="cgq-card cgq-how"><div className="cgq-side-head"><div><span className="cgq-kicker">BUILT AROUND YOUR PROGRESS</span><h2>How it adapts</h2></div><Sparkles size={19}/></div>
      <div className="cgq-how-item cgq-how-violet"><span className="cgq-how-icon"><Sparkles size={18}/></span><div><b>Smarter difficulty</b><small>{q?.difficulty?`Current question: ${String(q.difficulty)}`:'Uses your recorded quiz performance when selecting difficulty.'}</small></div><div className="cgq-ladder" aria-hidden="true"><i/><i/><i/></div></div>
      <div className="cgq-how-item cgq-how-amber"><span className="cgq-how-icon"><Lightbulb size={18}/></span><div><b>Hints, not answers</b><small>Use “I’m stuck” for available hints before submitting.</small></div></div>
      <div className="cgq-how-item cgq-how-coral"><span className="cgq-how-icon"><Target size={18}/></span><div><b>Topics to revisit</b><small>{topicSuggestions.length?`${topicSuggestions.length} topic${topicSuggestions.length===1?'':'s'} surfaced from your quiz history.`:'Review suggestions appear when enough quiz history is available.'}</small></div></div>
      <div className="cgq-side-footer"><ShieldCheck size={16}/><p>Your answer is counted only when the API confirms a saved result. Setup examples and animations are not quiz data.</p></div>
    </aside>
  </div>
</div>}
function todayISO(){
  const d=new Date();
  d.setHours(0,0,0,0);
  const pad=(n:number)=>String(n).padStart(2,'0');
  return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}`;
}

function WeeklySchedule({token,courseId}:any){
  const [weekStart,setWeekStart]=useState(()=>todayISO());
  const [minutes,setMinutes]=useState(30);
  const [saved,setSaved]=useState<any>(null);
  const [loading,setLoading]=useState(true);
  const [busy,setBusy]=useState(false);
  const [err,setErr]=useState('');
  const [generationNotice,setGenerationNotice]=useState<any>(null);
  const [updatingDate,setUpdatingDate]=useState('');
  const [selectedSessionDate,setSelectedSessionDate]=useState('');
  const [quizStats,setQuizStats]=useState<any>(null);

  useEffect(()=>{
    let active=true;
    request(`/api/courses/${courseId}/weak-topics`,token)
      .then((value:any)=>{if(active)setQuizStats(value?.stats||null)})
      .catch(()=>{if(active)setQuizStats(null)});
    return ()=>{active=false};
  },[token,courseId]);

  useEffect(()=>{
    const rows=Array.isArray(saved?.plan?.sessions)?saved.plan.sessions:[];
    if(!rows.length){setSelectedSessionDate('');return;}
    setSelectedSessionDate((current:string)=>{
      if(rows.some((row:any)=>row.date===current))return current;
      const today=todayISO();
      return rows.some((row:any)=>row.date===today)?today:rows[0].date;
    });
  },[saved,weekStart]);

  const selectedDate=new Date(`${weekStart}T00:00:00`);
  const selectedISO=Number.isNaN(selectedDate.getTime())?'':[
    selectedDate.getFullYear(),
    String(selectedDate.getMonth()+1).padStart(2,'0'),
    String(selectedDate.getDate()).padStart(2,'0')
  ].join('-');
  const validStartDate=/^\d{4}-\d{2}-\d{2}$/.test(weekStart)
    && selectedISO===weekStart;

  useEffect(()=>{
    let active=true;
    async function load(){
      setLoading(true);
      setErr('');
      try{
        const d=await request(
          `/api/courses/${courseId}/study-plan?week_start=${encodeURIComponent(weekStart)}`,
          token
        );
        if(active)setSaved(d.study_plan||null);
      }catch(e:any){
        if(active){
          setErr(e.message||'Could not load the saved study plan.');
          setSaved(null);
        }
      }finally{
        if(active)setLoading(false);
      }
    }
    if(courseId)load();
    return ()=>{active=false};
  },[token,courseId,weekStart]);

  async function generate(){
    if(!validStartDate){
      setErr('Please choose a valid start date.');
      return;
    }
    setBusy(true);
    setErr('');
    setGenerationNotice(null);
    try{
      const d=await request(
        `/api/courses/${courseId}/study-plan/generate?week_start=${encodeURIComponent(weekStart)}&minutes_per_day=${minutes}`,
        token,
        {method:'POST'}
      );
      const updatedPlan=d.study_plan||null;
      setSaved(updatedPlan);
      setGenerationNotice({
        attempts:updatedPlan?.plan?.basis?.recorded_attempts_considered,
        generatedAt:updatedPlan?.plan?.generated_at_utc
      });
    }catch(e:any){
      setErr(e.message||'Could not generate a study plan.');
    }finally{
      setBusy(false);
    }
  }


  async function toggleCompletion(session:any){
    if(updatingDate)return;
    const nextCompleted=!Boolean(session.completed);
    setUpdatingDate(session.date);
    setErr('');

    try{
      const result=await request(
        `/api/courses/${courseId}/study-plan/session`,
        token,
        {
          method:'POST',
          body:JSON.stringify({
            week_start:weekStart,
            session_date:session.date,
            completed:nextCompleted
          })
        }
      );

      setSaved((old:any)=>{
        if(!old?.plan||!Array.isArray(old.plan.sessions))return old;
        const updatedSessions=old.plan.sessions.map((item:any)=>
          item.date===session.date
            ? {...item,completed:Boolean(result.completed)}
            : item
        );
        return {
          ...old,
          completed_count:result.completed_count,
          total_sessions:result.total_sessions,
          plan:{...old.plan,sessions:updatedSessions}
        };
      });
    }catch(e:any){
      setErr(e.message||'Could not save session progress.');
    }finally{
      setUpdatingDate('');
    }
  }

  const plan=saved?.plan;
  const sessions=Array.isArray(plan?.sessions)?plan.sessions:[];
  const basis=plan?.basis;
  const generationTime=generationNotice?.generatedAt
    ? new Date(generationNotice.generatedAt) : null;
  const generationTimeLabel=generationTime && !Number.isNaN(generationTime.getTime())
    ? generationTime.toLocaleString() : 'just now';
  const completedCount=sessions.filter((session:any)=>session.completed).length;
  const progressPercent=sessions.length
    ? Math.round(completedCount/sessions.length*100) : 0;
  const selectedIndex=sessions.findIndex((session:any)=>session.date===selectedSessionDate);
  const selectedSession=selectedIndex>=0?sessions[selectedIndex]:null;

  return <div className="wsv2">
    <section className="wsv2-hero">
      <svg className="wsv2-hero-bg" viewBox="0 0 900 200" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
        <g stroke="#B8AFFF" strokeOpacity=".34" fill="none"><path d="M70 40 200 110 150 180M200 110 360 50 470 140 360 190M470 140 620 50M620 50 760 130 860 40"/></g>
        <g><circle cx="70" cy="40" r="5" fill="#B8AFFF"/><circle cx="200" cy="110" r="7" fill="#5EEAD4"/><circle cx="360" cy="50" r="6" fill="#B8AFFF"/><circle cx="470" cy="140" r="8" fill="#FFC86B"/><circle cx="620" cy="50" r="5" fill="#5EEAD4"/><circle cx="760" cy="130" r="6" fill="#B8AFFF"/></g>
      </svg>
      <div className="wsv2-hero-copy"><span className="wsv2-eyebrow">PERSONALIZED LEARNING · WEEKLY PLAN</span><h1>Plan your week.</h1><p>Seven focused sessions, shaped by your real course material and quiz history.</p></div>
      <div className="wsv2-thinker">
        <svg className="wsv2-person" viewBox="0 0 120 132" fill="none" role="img" aria-label="A student thinking"><path d="M12 132C12 102 34 90 60 90s48 12 48 42z" fill="#6C5CE7"/><rect x="53" y="76" width="14" height="17" rx="5" fill="#E8B98F"/><ellipse cx="60" cy="52" rx="22" ry="26" fill="#F2C9A5"/><path d="M37 52c-4-24 12-32 25-31 17 1 24 14 21 31-5-12-15-16-27-15-9 1-15 6-19 15z" fill="#4A3FB0"/><path d="M47 46q5-3 10 0M64 44q5-3 10 0" stroke="#2A2166" strokeWidth="2" strokeLinecap="round"/><circle cx="54" cy="52" r="2.6" fill="#120F2E"/><circle cx="71" cy="50" r="2.6" fill="#120F2E"/><path d="M55 66q5-2 9 0" stroke="#9A5B4A" strokeWidth="2" strokeLinecap="round"/><path d="M92 126 84 98 70 76" stroke="#6C5CE7" strokeWidth="14" strokeLinecap="round" strokeLinejoin="round"/><circle cx="68" cy="72" r="8" fill="#F2C9A5"/></svg>
        <div className="wsv2-bubble"><b><span className="wsv2-live-dot"/>Ask yourself</b><p>How will you know you are done?</p></div>
      </div>
    </section>

    <section className="wsv2-stats" aria-label="Real study-plan progress">
      <article className="wsv2-stat wsv2-stat-violet"><span className="wsv2-stat-icon"><CheckCircle2 size={19}/></span><div><strong>{completedCount} / {sessions.length || 7}</strong><b>Sessions done</b><small>{sessions.length ? `${progressPercent}% of this plan completed` : 'Generate a plan to begin tracking'}</small></div><div className="wsv2-mini-progress" aria-hidden="true">{Array.from({length:7},(_,i)=><i key={i} className={i<completedCount?'on':''}/>)}</div></article>
      <article className="wsv2-stat wsv2-stat-amber"><span className="wsv2-stat-icon"><Clock3 size={19}/></span><div><strong>{selectedSession?.duration_minutes ?? minutes} min</strong><b>Per study day</b><small>{plan ? 'From the saved plan' : 'Your selected daily target'}</small></div></article>
      <article className="wsv2-stat wsv2-stat-teal"><span className="wsv2-stat-icon"><Target size={19}/></span><div><strong>{typeof basis?.recorded_attempts_considered==='number' ? basis.recorded_attempts_considered : (typeof quizStats?.attempts==='number' ? quizStats.attempts : '—')}</strong><b>{basis ? 'Attempts considered' : 'Saved quiz attempts'}</b><small>{basis ? 'Reliable attempts used for this plan' : 'Recorded for this course'}</small></div></article>
    </section>

    <div className="wsv2-layout">
      <aside className="wsv2-panel wsv2-controls">
        <div className="wsv2-panel-title"><span className="wsv2-control-icon"><CalendarDays size={19}/></span><h2>Plan your week</h2></div>
        <p className="wsv2-muted">Choose a start date and daily study time. Your plan is saved to this course and week.</p>
        <label className="wsv2-label" htmlFor="wsv2-start">Start date</label>
        <input id="wsv2-start" className="wsv2-date" type="date" value={weekStart} onChange={e=>{setWeekStart(e.target.value);setGenerationNotice(null);}}/>
        {!validStartDate&&<p className="wsv2-field-error">Choose a valid start date to continue.</p>}
        <div className="wsv2-label"><Clock3 size={15}/> Minutes per day</div>
        <div className="wsv2-minute-options" role="group" aria-label="Minutes per study day">{[15,30,45,60].map(value=><button type="button" key={value} aria-pressed={minutes===value} onClick={()=>setMinutes(value)} disabled={busy||loading}>{value}<small>min</small></button>)}</div>
        <button type="button" className="wsv2-generate" onClick={generate} disabled={busy||loading||!validStartDate}>{busy?<LoaderCircle size={17} className="wsv2-spin"/>:<Sparkles size={17}/>} {busy?'Generating plan…':'Generate study plan'}</button>
        {loading&&<p className="wsv2-status"><LoaderCircle size={14} className="wsv2-spin"/> Loading the saved plan for this week…</p>}
        {err&&<div className="wsv2-alert" role="alert">{err}</div>}
        {generationNotice&&<div className="wsv2-saved-notice" role="status"><CheckCircle2 size={15}/><div><b>Study plan saved</b><small>{typeof generationNotice.attempts==='number' ? `${generationNotice.attempts} reliable quiz attempts considered.` : 'Attempt count was not provided.'}</small><small>Generated {generationTimeLabel}.</small></div></div>}
        <p className="wsv2-save-note"><CheckCircle2 size={14}/> Saved to this course and selected week</p>
      </aside>

      <main className="wsv2-main">
        <section className="wsv2-panel wsv2-week-panel">
          <div className="wsv2-week-heading"><div><h2>Your seven-day plan</h2><p>{weekStart ? `Starting ${new Date(`${weekStart}T00:00:00`).toLocaleDateString(undefined,{day:'numeric',month:'short',year:'numeric'})}` : 'Choose a start date'}</p></div>{plan&&<span className="wsv2-plan-tag"><RefreshCw size={12}/>{plan.mode==='weak-topic-focused'?'Weak-topic focused':plan.mode==='consolidation'?'Topic consolidation':'Starter plan'}</span>}</div>
          {plan?.explanation&&<p className="wsv2-plan-explanation">{plan.explanation}</p>}
          {loading ? <div className="wsv2-empty"><LoaderCircle size={22} className="wsv2-spin"/> Loading saved plan…</div>
          : sessions.length ? <div className="wsv2-day-strip" role="tablist" aria-label="Choose a study day">{sessions.map((session:any,index:number)=>{
              const dt=new Date(`${session.date}T00:00:00`);
              const dayName=String(session.day||dt.toLocaleDateString(undefined,{weekday:'short'})).slice(0,3);
              const dayNumber=dt.getDate();
              const dayColor=['#6C5CE7','#14B8A6','#F5A524','#F4647B','#D946A8','#0EA5E9','#22A06B'][index%7];
              const isToday=session.date===todayISO();
              return <button type="button" key={session.date} role="tab" aria-selected={session.date===selectedSessionDate} className={`wsv2-day ${session.completed?'is-done':''}`} style={{'--wsv2-day':dayColor} as React.CSSProperties} onClick={()=>setSelectedSessionDate(session.date)}><span className="wsv2-day-name">{dayName}</span><b>{dayNumber}</b><span className="wsv2-day-icon">{session.completed?<CheckCircle2 size={16}/>:index===0?<Target size={16}/>:index===1?<RefreshCw size={16}/>:index===2?<BookOpen size={16}/>:index===3?<BrainCircuit size={16}/>:index===4?<PencilLine size={16}/>:index===5?<Sparkles size={16}/>:<CheckCircle2 size={16}/>}</span>{isToday&&<span className="wsv2-today">Today</span>}</button>;
            })}</div>
          : <div className="wsv2-empty-plan"><div className="wsv2-empty-icon"><CalendarDays size={25}/></div><h3>No saved plan for this week</h3><p>Generate a plan to get seven sessions built from your recorded quiz results and course topics. We won’t invent activities before a plan exists.</p><button type="button" className="wsv2-generate wsv2-inline-generate" onClick={generate} disabled={busy||!validStartDate}>{busy?<LoaderCircle size={16} className="wsv2-spin"/>:<Sparkles size={16}/>} Generate your seven-day plan</button></div>}
        </section>

        {selectedSession&&<section className="wsv2-panel wsv2-detail" style={{'--wsv2-accent':['#6C5CE7','#14B8A6','#F5A524','#F4647B','#D946A8','#0EA5E9','#22A06B'][Math.max(0,selectedIndex)%7]} as React.CSSProperties}>
          <div className="wsv2-detail-head"><span className="wsv2-detail-icon"><Target size={21}/></span><div className="wsv2-detail-title"><div className="wsv2-detail-date">{new Date(`${selectedSession.date}T00:00:00`).toLocaleDateString(undefined,{weekday:'long',day:'numeric',month:'short'})}<span>{String(selectedSession.session_type||'study').replace(/-/g,' ')}</span></div><h2>{selectedSession.topic}</h2>{selectedSession.focus&&selectedSession.focus!==selectedSession.topic&&<p className="wsv2-focus">Focus · {selectedSession.focus}</p>}{selectedSession.objective&&<p className="wsv2-objective">{selectedSession.objective}</p>}</div></div>
          <div className="wsv2-step-progress" aria-label={`${Array.isArray(selectedSession.activities)?selectedSession.activities.length:0} study activities`}>{(Array.isArray(selectedSession.activities)?selectedSession.activities:[]).map((_:any,i:number)=><i key={i}/>)}</div>
          {Array.isArray(selectedSession.activities)&&selectedSession.activities.length>0?<div className="wsv2-activities">{selectedSession.activities.map((activity:any,i:number)=>{const ActivityIcon=i===0?BookOpen:i===1?PencilLine:BrainCircuit;return <article className="wsv2-activity" key={`${selectedSession.date}-${i}`}><div className="wsv2-activity-top"><span className="wsv2-activity-number">{i+1}</span><span className="wsv2-activity-time">{activity.minutes} min</span></div><h3><ActivityIcon size={16}/>{activity.title}</h3><p>{activity.instruction}</p></article>})}</div>:<p className="wsv2-objective">{selectedSession.task||'Review the selected topic.'}</p>}
          {selectedSession.success_criteria&&<div className="wsv2-done-when"><span><CheckCircle2 size={17}/></span><div><b>Done when</b><p>{selectedSession.success_criteria}</p></div></div>}
          <div className="wsv2-detail-footer"><span className="wsv2-duration"><Clock3 size={15}/>{selectedSession.duration_minutes} minutes</span><span className="wsv2-footer-spacer"/><button type="button" className={`wsv2-complete ${selectedSession.completed?'is-complete':''}`} onClick={()=>toggleCompletion(selectedSession)} disabled={Boolean(updatingDate)}>{updatingDate===selectedSession.date?<LoaderCircle size={15} className="wsv2-spin"/>:<CheckCircle2 size={15}/>} {updatingDate===selectedSession.date?'Saving…':selectedSession.completed?'Completed · Mark incomplete':'Mark complete'}</button></div>
        </section>}
      </main>
    </div>
  </div>;
}

function cgRevKey(value:string){return String(value||'').toLowerCase().replace(/[`*_]/g,'').replace(/[^a-z0-9]+/g,' ').trim()}
function cgRevSections(markdown:string){
  const out:any[]=[];let section:any=null;
  const push=()=>{if(section)out.push({title:section.title,key:cgRevKey(section.title),body:section.lines.join('\n').trim()});section=null};
  String(markdown||'').replace(/\r\n/g,'\n').split('\n').forEach(line=>{
    const h=line.match(/^\s{0,3}(#{1,4})\s+(.+?)\s*#*\s*$/);
    if(h){push();section={title:h[2].trim(),lines:[]}}else if(section)section.lines.push(line);
  });push();
  if(!out.length&&String(markdown||'').trim())out.push({title:'Revision notes',key:'revision notes',body:String(markdown).trim()});
  return out;
}
function cgRevFind(sections:any[],names:string[]){const keys=names.map(cgRevKey);return sections.find((s:any)=>keys.some(k=>s.key===k||s.key.startsWith(k+' ')))||null}
function cgRevItems(body:string){
  const out:string[]=[];let current='';const flush=()=>{if(current.trim())out.push(current.trim());current=''};
  for(const raw of String(body||'').split('\n')){const line=raw.trim();if(!line){flush();continue}
    const m=line.match(/^(?:[-*+]\s+|\d{1,2}\s*[.)]\s+|(?:question|q)\s*\d{1,2}\s*[:.)-]\s*)(.+)$/i);
    const h=line.match(/^#{2,4}\s+(.+)$/);
    if(m||h){flush();current=(m?m[1]:h![1]).trim()}else if(current)current+=' '+line;else current=line;
  }flush();return out.filter(x=>x&&!/^sources?\s*:/i.test(x));
}
function Revision({token,courseId,initialTopic}:any){
  const [topic,setTopic]=useState(String(initialTopic||''));const [data,setData]=useState<any>(null);const [weak,setWeak]=useState<any[]>([]);
  const [busy,setBusy]=useState(false);const [weakLoading,setWeakLoading]=useState(true);const [err,setErr]=useState('');
  const [view,setView]=useState('review');const [moreIdeas,setMoreIdeas]=useState(false);const [questionIndex,setQuestionIndex]=useState(0);
  const [revealed,setRevealed]=useState(false);const [copyLabel,setCopyLabel]=useState('Copy notes');const [thinkIndex,setThinkIndex]=useState(0);
  const thoughts=['Turn course notes into useful recall prompts.','Keep the important ideas short.','Connect revision to your selected course.'];
  useEffect(()=>{const id=window.setInterval(()=>setThinkIndex(n=>(n+1)%thoughts.length),4300);return()=>window.clearInterval(id)},[]);
  useEffect(()=>{let live=true;setData(null);setWeak([]);setErr('');setWeakLoading(true);
    request(`/api/courses/${courseId}/weak-topics`,token).then(d=>{if(live)setWeak(Array.isArray(d.topics)?d.topics:[])}).catch(()=>{if(live)setWeak([])}).finally(()=>{if(live)setWeakLoading(false)});
    request(`/api/courses/${courseId}/revision/latest`,token).then(d=>{if(live&&d?.revision)setData(d.revision)}).catch(()=>{});
    return()=>{live=false};
  },[courseId,token]);
  const revision=data?.revision||data?.data||data;
  const markdown=typeof revision?.content==='string'?revision.content:(typeof revision?.markdown==='string'?revision.markdown:(typeof revision==='string'?revision:''));
  const sections=useMemo(()=>cgRevSections(markdown),[markdown]);
  const recap=cgRevFind(sections,['quick recap','30 second recap','core idea','central idea','main takeaway']);
  const ideas=cgRevFind(sections,['key ideas','key ideas to remember','key points','key takeaways','remember these'])||cgRevFind(sections,['correct reasoning']);
  const results=cgRevFind(sections,['what your quiz results show','your quiz results','quiz results','recorded quiz statistics']);
  const mistake=cgRevFind(sections,['what went wrong','where you slipped','common confusion','common mix up','common mistakes','misconceptions']);
  const practice=cgRevFind(sections,['check yourself','quick self check','quick self-check','practice questions','self check','self test']);
  const key=cgRevFind(sections,['answer key','answers','practice answers','self check answers']);
  const ideaItems=useMemo(()=>{const xs=cgRevItems(ideas?.body||'');return xs.length?xs:(recap?.body?[recap.body]:[])},[ideas?.body,recap?.body]);
  const questions=useMemo(()=>cgRevItems(practice?.body||''),[practice?.body]);const answers=useMemo(()=>cgRevItems(key?.body||''),[key?.body]);
  const topics=Array.isArray(revision?.topics)?revision.topics.filter(Boolean):[];const hasData=Boolean(markdown);const sources=Array.isArray(revision?.sources)?revision.sources:[];
  const shownIdeas=moreIdeas?ideaItems:ideaItems.slice(0,3);const q=questions[questionIndex]||'';const a=answers[questionIndex]||'';
  useEffect(()=>{setQuestionIndex(0);setRevealed(false);setMoreIdeas(false);setView('review')},[markdown]);
  async function generate(t=topic){if(busy)return;setBusy(true);setErr('');setCopyLabel('Copy notes');try{
    const d=await request('/api/revision',token,{method:'POST',body:JSON.stringify({course_id:courseId,topic:t})});
    if(!d||typeof d.content!=='string'||!d.content.trim())throw new Error('The revision service returned an empty sheet. Try a more specific topic.');
    setData(d);setView('review');setQuestionIndex(0);setRevealed(false);setMoreIdeas(false);setTopic(t==='__weak_topics__'?'':t);
  }catch(e:any){setErr(e?.message||'Revision could not be generated. Please try again.')}finally{setBusy(false)}}
  async function copyNotes(){if(!markdown)return;try{if(navigator.clipboard&&window.isSecureContext)await navigator.clipboard.writeText(markdown);else throw new Error('Clipboard unavailable');setCopyLabel('Copied')}catch{try{const el=document.createElement('textarea');el.value=markdown;el.setAttribute('readonly','');el.style.position='fixed';el.style.left='-9999px';document.body.appendChild(el);el.select();const ok=document.execCommand('copy');el.remove();if(!ok)throw new Error('Copy failed');setCopyLabel('Copied')}catch{setErr('Copy failed. Open Full notes and select the text to copy it manually.')}}window.setTimeout(()=>setCopyLabel('Copy notes'),1800)}
  const focus=topics.length?topics.join(', '):(topic.trim()||'Selected course material');
  return <div className="revision-v2">
    <section className="rev2-hero"><svg className="rev2-network" viewBox="0 0 900 220" preserveAspectRatio="xMidYMid slice" aria-hidden="true"><g stroke="#B8AFFF" strokeOpacity=".28" fill="none"><path d="M70 40 200 120 150 190M200 120 360 60 470 150 360 200M470 150 620 60M620 60 760 140 860 50"/></g><g><circle cx="70" cy="40" r="5" fill="#B8AFFF"/><circle cx="200" cy="120" r="7" fill="#5EEAD4"/><circle cx="360" cy="60" r="6" fill="#B8AFFF"/><circle cx="470" cy="150" r="8" fill="#FFC86B"/><circle cx="620" cy="60" r="5" fill="#5EEAD4"/><circle cx="760" cy="140" r="6" fill="#B8AFFF"/></g></svg>
      <div className="rev2-hero-copy"><span className="rev2-eyebrow">REVISION MODE · ACTIVE RECALL</span><h1>Revise what matters.</h1><p>Short, course-grounded prompts first. Deeper notes only when you need them.</p></div>
      <div className="rev2-thinker"><svg className="rev2-person" viewBox="0 0 120 132" fill="none" role="img" aria-label="A person thinking"><path d="M12 132C12 102 34 90 60 90s48 12 48 42z" fill="#6C5CE7"/><rect x="53" y="76" width="14" height="17" rx="5" fill="#E8B98F"/><ellipse cx="60" cy="52" rx="22" ry="26" fill="#F2C9A5"/><path d="M37 52c-4-24 12-32 25-31 17 1 24 14 21 31-5-12-15-16-27-15-9 1-15 6-19 15z" fill="#4A3FB0"/><path d="M47 46q5-3 10 0M64 44q5-3 10 0" stroke="#2A2166" strokeWidth="2" strokeLinecap="round"/><circle cx="54" cy="52" r="2.6" fill="#120F2E"/><circle cx="71" cy="50" r="2.6" fill="#120F2E"/><path d="M55 66q5-2 9 0" stroke="#9A5B4A" strokeWidth="2" strokeLinecap="round"/><path d="M92 126 84 98 70 76" stroke="#6C5CE7" strokeWidth="14" strokeLinecap="round" strokeLinejoin="round"/><circle cx="68" cy="72" r="8" fill="#F2C9A5"/></svg><div className="rev2-bubble"><b><span className="rev2-live-dot"/> Thinking…</b><span key={thinkIndex}>{thoughts[thinkIndex]}</span></div></div>
    </section>
    <div className="rev2-layout"><aside className="rev2-sidebar"><section className="rev2-panel rev2-generator">
      <div className="rev2-panel-title"><span className="rev2-icon rev2-amber"><BookOpen size={18}/></span><h2>What do you want to revise?</h2></div><p className="rev2-muted">Choose a topic, or focus on real gaps from your quiz attempts.</p>
      <label className="rev2-label" htmlFor="rev2-topic">Topic</label><input id="rev2-topic" className="rev2-topic-input" value={topic} onChange={e=>setTopic(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'&&!busy)generate(topic)}} placeholder="e.g. Logistic Regression"/>
      <button className="rev2-primary" onClick={()=>generate(topic)} disabled={busy}>{busy?<LoaderCircle size={16} className="rev2-spin"/>:<Sparkles size={16}/>}{busy?'Building a focused review…':'Generate revision'}</button>
      <button className="rev2-secondary" onClick={()=>generate('__weak_topics__')} disabled={busy||weak.length===0}><Target size={16}/> Revise my weak topics</button>{err&&<div className="rev2-alert" role="alert">{err}</div>}
      <div className="rev2-weak-head"><span>Weak topics</span><span className="rev2-weak-note">{weakLoading?'Loading…':weak.length?`${weak.length} found`:'No confirmed weak topics yet'}</span></div>
      {weakLoading?<div className="rev2-skeleton" aria-label="Loading weak topics"><i/><i/></div>:weak.length?<div className="rev2-weak-list">{weak.slice(0,4).map((w:any)=><button className="rev2-weak-row" key={w.topic} onClick={()=>{setTopic(w.topic);generate(w.topic)}} disabled={busy}><span className="rev2-weak-mark"><Target size={14}/></span><span className="rev2-weak-copy"><b>{w.topic}</b><span>{Number.isFinite(Number(w.accuracy))?`${Math.round(Number(w.accuracy)*100)}% recorded accuracy`:`${w.attempts||0} recorded attempts`}</span></span><span className="rev2-weak-arrow">↗</span></button>)}</div>:<p className="rev2-empty-weak">Weak topics appear after enough usable quiz attempts. You can still review any indexed topic.</p>}
    </section><section className="rev2-tip"><Lightbulb size={17}/><div><b>Try this flow</b><p>Read a short idea, explain it in your own words, then reveal an answer in Practice.</p></div></section></aside>
    <main className="rev2-main">{hasData?<section className="rev2-panel rev2-output"><header className="rev2-output-head"><div className="rev2-output-ident"><span className="rev2-icon rev2-teal"><BookOpen size={18}/></span><div><h2>Revision workspace</h2><p>{focus}</p></div></div><button className="rev2-copy" onClick={copyNotes}><FileText size={14}/>{copyLabel}</button></header>
      <div className="rev2-tabs" role="tablist" aria-label="Revision views"><button role="tab" aria-selected={view==='review'} className={view==='review'?'active':''} onClick={()=>setView('review')}>Quick review</button><button role="tab" aria-selected={view==='practice'} className={view==='practice'?'active':''} onClick={()=>setView('practice')}>Practice{questions.length?` · ${questions.length}`:''}</button><button role="tab" aria-selected={view==='notes'} className={view==='notes'?'active':''} onClick={()=>setView('notes')}>Full notes</button></div>
      {view==='review'&&<div className="rev2-review">
        {results&&<section className="rev2-focus"><div className="rev2-section-label"><span className="rev2-section-dot rev2-dot-violet"/>Your recorded quiz results</div><div className="rev2-md"><ReactMarkdown remarkPlugins={[remarkGfm]}>{results.body}</ReactMarkdown></div></section>}
        {recap&&<section className="rev2-recap"><div className="rev2-section-label"><span className="rev2-section-dot rev2-dot-teal"/>Quick recap</div><div className="rev2-md"><ReactMarkdown remarkPlugins={[remarkGfm]}>{recap.body}</ReactMarkdown></div></section>}
        <section className="rev2-ideas"><div className="rev2-section-heading"><div><h3>Key ideas</h3><p>Short reminders, not another chapter to read.</p></div><span className="rev2-count">{ideaItems.length}</span></div>
          {shownIdeas.length?<div className="rev2-idea-list">{shownIdeas.map((idea:string,i:number)=><article className={`rev2-idea rev2-idea-${i%3}`} key={`${i}-${idea.slice(0,30)}`}><span className="rev2-idea-number">{String(i+1).padStart(2,'0')}</span><div className="rev2-md"><ReactMarkdown remarkPlugins={[remarkGfm]}>{idea}</ReactMarkdown></div></article>)}</div>:<div className="rev2-no-structured"><b>No separate key-idea list was returned.</b><p>The original source-grounded material remains available under Full notes. We won't invent cards from unstructured prose.</p></div>}
          {ideaItems.length>3&&<button className="rev2-text-action" onClick={()=>setMoreIdeas(v=>!v)}>{moreIdeas?'Show only the first 3 ideas':`Show all ${ideaItems.length} ideas`} <span>{moreIdeas?'↑':'↓'}</span></button>}
        </section>
        {mistake&&<section className="rev2-mistake"><div className="rev2-section-heading"><div><h3>{/wrong|slipped|mistake|misconception/i.test(mistake.title)?mistake.title:'Common mix-up'}</h3><p>{/wrong|slipped|mistake/i.test(mistake.title)?'Use the correction to update your mental model.':'A distinction worth remembering.'}</p></div><span className="rev2-icon rev2-coral"><CircleHelp size={17}/></span></div><div className="rev2-md"><ReactMarkdown remarkPlugins={[remarkGfm]}>{mistake.body}</ReactMarkdown></div></section>}
        {sources.length>0&&<section className="rev2-sources"><div className="rev2-section-label"><span className="rev2-section-dot rev2-dot-amber"/>Grounded in your course</div><div className="rev2-source-list">{sources.map((s:any,i:number)=><div className="rev2-source" key={`${s.source||'source'}-${s.page??i}`}><FileText size={14}/><span><b>{s.source||'Course source'}</b><small>{s.page!=null?`Page ${s.page}`:'Page not provided by source record'}</small></span></div>)}</div></section>}
        <button className="rev2-open-practice" onClick={()=>setView('practice')} disabled={!questions.length}><span><Sparkles size={17}/></span><div><b>Check what you remember</b><small>{questions.length?`${questions.length} question${questions.length===1?'':'s'} · one at a time, answers hidden`:'No structured self-check questions in this response'}</small></div><span className="rev2-arrow">→</span></button>
      </div>}
      {view==='practice'&&<section className="rev2-practice"><div className="rev2-section-heading"><div><h3>Check yourself</h3><p>Answer from memory before revealing the key. Questions are shown one at a time.</p></div>{questions.length>0&&<span className="rev2-count">{questionIndex+1} / {questions.length}</span>}</div>
        {questions.length?<><div className="rev2-practice-progress"><span style={{width:`${((questionIndex+1)/questions.length)*100}%`}}/></div><article className="rev2-question"><div className="rev2-question-kicker">QUESTION {questionIndex+1}</div><div className="rev2-question-text"><ReactMarkdown remarkPlugins={[remarkGfm]}>{q}</ReactMarkdown></div>
          {revealed&&<div className="rev2-answer"><b>Answer key</b>{a?<div className="rev2-md"><ReactMarkdown remarkPlugins={[remarkGfm]}>{a}</ReactMarkdown></div>:<p>This revision did not return a matching answer. Check Full notes rather than guessing.</p>}</div>}
          <div className="rev2-practice-actions"><button className="rev2-reveal" onClick={()=>setRevealed(v=>!v)} disabled={!a}>{revealed?'Hide answer':'Reveal answer'}</button><div className="rev2-nextprev"><button onClick={()=>{setQuestionIndex(i=>Math.max(0,i-1));setRevealed(false)}} disabled={questionIndex===0}>← Previous</button><button onClick={()=>{setQuestionIndex(i=>Math.min(questions.length-1,i+1));setRevealed(false)}} disabled={questionIndex>=questions.length-1}>Next →</button></div></div>
          {!a&&<p className="rev2-small-warning">No matching answer-key item was generated for this question.</p>}</article></>:<div className="rev2-no-structured"><b>No structured practice questions were returned.</b><p>Open Full notes to read the complete revision, or regenerate for a more specific topic.</p><button className="rev2-secondary" onClick={()=>setView('notes')}>Open full notes</button></div>}
      </section>}
      {view==='notes'&&<section className="rev2-fullnotes"><div className="rev2-section-heading"><div><h3>Full revision notes</h3><p>Original generated content, kept intact for detail and citations.</p></div></div><div className="rev2-md rev2-markdown-full"><ReactMarkdown remarkPlugins={[remarkGfm]}>{markdown}</ReactMarkdown></div></section>}
    </section>:<section className="rev2-panel rev2-empty-output"><div className="rev2-empty-illustration"><BookOpen size={28}/></div><span className="rev2-eyebrow">READY WHEN YOU ARE</span><h2>Make revision active, not exhausting.</h2><p>Choose a topic or a confirmed weak topic. CogniGraph will build a short recap, key ideas, and self-check questions from the selected course material.</p><div className="rev2-empty-steps"><span><b>01</b> Read a concise idea</span><span><b>02</b> Recall it without notes</span><span><b>03</b> Reveal the answer</span></div></section>}</main></div>
  </div>;
}
function Weak({token,courseId,setPage,setWeakTargetTopic,setPracticeWeakTopics}:any){
  const [data,setData]=useState<any>(null);
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState('');
  const [reloadKey,setReloadKey]=useState(0);
  const [selectedTopicIndex,setSelectedTopicIndex]=useState<number|null>(null);
  useEffect(()=>{
    let active=true;
    setLoading(true);setError('');
    request(`/api/courses/${courseId}/weak-topics`,token)
      .then((d:any)=>{if(active)setData(d||null)})
      .catch((e:any)=>{if(active){setData(null);setError(e?.message||'Could not load your saved quiz statistics.')}})
      .finally(()=>{if(active)setLoading(false)});
    return ()=>{active=false};
  },[courseId,token,reloadKey]);

  const stats=data?.stats||null;
  const topics=Array.isArray(data?.topics)?data.topics.filter((t:any)=>typeof t?.topic==='string'&&t.topic.trim()):[];
  const attempts=stats&&Number.isFinite(Number(stats.attempts))?Number(stats.attempts):null;
  const accuracy=stats&&stats.accuracy!==null&&stats.accuracy!==undefined&&Number.isFinite(Number(stats.accuracy))?Math.max(0,Math.min(100,Math.round(Number(stats.accuracy)*100))):null;
  const difficulty=typeof data?.difficulty==='string'&&data.difficulty.trim()?data.difficulty:'—';
  const topicRate=(value:any)=>value===null||value===undefined||value===''?null:(Number.isFinite(Number(value))?Math.max(0,Math.min(1,Number(value))):null);
  const topicAttempts=(t:any)=>Math.max(0,Number(t?.attempts)||0);
  const maxTopicAttempts=topics.length?Math.max(...topics.map(topicAttempts)):0;
  const evidenceLevel=!topics.length?0:maxTopicAttempts<=1?1:maxTopicAttempts<4?2:3;
  const evidenceText=evidenceLevel===0?'A few saved quizzes help CogniGraph begin identifying patterns.':evidenceLevel===1?'One attempt is an early signal. More quizzes help confirm whether the gap persists.':evidenceLevel===2?'Repeated saved attempts provide a stronger signal; keep practicing to build confidence.':'Several saved attempts support this signal. Recheck it as you complete more quizzes.';
  const mapPoints=[[66,72],[184,105],[257,48],[134,163]];
  const mapTopics=topics.slice(0,4);
  const rateColor=(rate:number|null)=>rate===null?'#8B80F6':rate<=0.4?'#F4647B':rate<=0.7?'#F5A524':'#14B8A6';
  const topicInitials=(value:string)=>String(value||'').trim().split(/\s+/).filter(Boolean).slice(0,3).map((word:string)=>word[0]).join('').toUpperCase().slice(0,3)||'?';
  function goRevise(topic:string){setWeakTargetTopic(topic);setPracticeWeakTopics(false);setPage('revision')}
  function goQuiz(topic:string){setWeakTargetTopic(topic);setPracticeWeakTopics(false);setPage('quiz')}
  function practiceAll(){setWeakTargetTopic('');setPracticeWeakTopics(true);setPage('quiz')}
  function jumpToTopic(index:number){const list=document.querySelector('.weakv2-topic-list') as HTMLElement|null;const card=document.getElementById(`weak-topic-${index}`);if(!card)return;setSelectedTopicIndex(index);if(list&&list.contains(card)){list.scrollTo({top:Math.max(0,card.offsetTop-6),behavior:'smooth'});}}

  return <div className="weak-v2">
    <section className="weakv2-hero">
      <svg className="weakv2-network" viewBox="0 0 900 200" preserveAspectRatio="xMidYMid slice" aria-hidden="true"><g stroke="#B8AFFF" strokeOpacity=".34" fill="none"><path d="M70 40 200 110 150 180M200 110 360 50 470 140 360 190M470 140 620 50M620 50 760 130 860 40"/></g><g><circle cx="70" cy="40" r="5" fill="#B8AFFF"/><circle cx="200" cy="110" r="7" fill="#F4647B"/><circle cx="360" cy="50" r="6" fill="#B8AFFF"/><circle cx="470" cy="140" r="8" fill="#FFC86B"/><circle cx="620" cy="50" r="5" fill="#5EEAD4"/><circle cx="760" cy="130" r="6" fill="#B8AFFF"/></g></svg>
      <div className="weakv2-hero-copy"><span className="weakv2-kicker">PERSONALIZED LEARNING · SAVED QUIZ EVIDENCE</span><h1>Find your weak spots.</h1><p>See where a little practice helps most. Suggestions come from recorded quiz attempts, not guesses.</p></div>
      <div className="weakv2-ask"><span><i/> Ask yourself</span><p>{topics[0]?.topic?`What is still tricky about ${topics[0].topic}?`:'What would you like to strengthen today?'}</p></div>
    </section>

    <section className="weakv2-stats" aria-label="Recorded course statistics">
      <article className="weakv2-stat weakv2-stat-violet"><span className="weakv2-stat-icon"><CircleHelp size={19}/></span><div><strong>{loading?'…':attempts===null?'—':attempts}</strong><b>Quiz attempts</b><small>{attempts===null?'Saved progress unavailable':'Across saved answers'}</small></div></article>
      <article className="weakv2-stat weakv2-stat-amber"><span className="weakv2-stat-icon"><Target size={19}/></span><div><strong>{loading?'…':accuracy===null?'—':`${accuracy}%`}</strong><b>Overall accuracy</b><small>{accuracy===null?'No recorded accuracy yet':'From saved quiz attempts'}</small></div></article>
      <article className="weakv2-stat weakv2-stat-teal"><span className="weakv2-stat-icon"><Sparkles size={19}/></span><div><strong>{loading?'…':difficulty}</strong><b>Suggested difficulty</b><small>Based on saved performance</small><span className="weakv2-level-bars" aria-hidden="true"><i/><i/><i/></span></div></article>
    </section>

    {error&&<div className="weakv2-error" role="alert"><span>{error}</span><button type="button" onClick={()=>setReloadKey((n:number)=>n+1)}>Retry <RefreshCw size={14}/></button></div>}

    <div className="weakv2-layout">
      <section className="weakv2-panel weakv2-topics-panel">
        <header className="weakv2-panel-head"><div className="weakv2-panel-title"><span className="weakv2-title-icon"><BookOpen size={18}/></span><h2>Topics to revisit</h2><span className="weakv2-count">{loading?'…':topics.length}</span></div><button className="weakv2-primary" type="button" onClick={practiceAll} disabled={loading||topics.length===0}><ChevronRight size={15}/> Practice all</button></header>
        <p className="weakv2-subtitle">One missed answer is an early signal. Repeated attempts give you a clearer picture.</p>
        {loading?<div className="weakv2-loading" role="status"><i/><i/><i/></div>:topics.length? <div className="weakv2-topic-list">{topics.map((t:any,index:number)=>{
          const rate=topicRate(t.accuracy);const pct=rate===null?null:Math.round(rate*100);const tone=rateColor(rate);const nAttempts=topicAttempts(t);const missed=Math.max(0,Number(t?.incorrect)||0);
          return <article className={`weakv2-topic ${selectedTopicIndex===index?"is-selected":""}`} id={`weak-topic-${index}`} key={`${t.topic}-${index}`} style={{'--weakv2-tone':tone} as React.CSSProperties}>
            <div className="weakv2-topic-row"><span className="weakv2-topic-icon"><Target size={17}/></span><div className="weakv2-topic-copy"><h3>{t.topic}</h3><div className="weakv2-chips"><span>{nAttempts} {nAttempts===1?'attempt':'attempts'}</span>{missed>0&&<span className="weakv2-missed"><CircleHelp size={11}/>{missed} missed</span>}</div></div><strong className="weakv2-percent">{pct===null?'—':`${pct}%`}</strong></div>
            <div className="weakv2-progress" role="progressbar" aria-label={`${t.topic} accuracy`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={pct===null?0:pct}><span style={{width:`${pct===null?0:pct}%`}}/></div>
            <div className="weakv2-topic-actions"><button type="button" className="weakv2-secondary" onClick={()=>goRevise(String(t.topic))}><BookOpen size={14}/> Revise</button><button type="button" className="weakv2-tertiary" onClick={()=>goQuiz(String(t.topic))}><CircleHelp size={14}/> Quiz me</button></div>
          </article>;
        })}</div>:<div className="weakv2-empty"><span><Target size={23}/></span><h3>{error?'Your topics could not be loaded':'No weak topics identified yet'}</h3><p>{error?'Retry the request to reload your saved quiz statistics.':'Complete a quiz from your selected course. CogniGraph will use eligible recorded attempts to surface topics worth revisiting.'}</p>{!error&&<button type="button" className="weakv2-secondary" onClick={()=>setPage('quiz')}><CircleHelp size={14}/> Go to Quiz Mode</button>}</div>}
      </section>

      <aside className="weakv2-side">
        <section className="weakv2-panel weakv2-map-panel"><header className="weakv2-panel-head"><div className="weakv2-panel-title"><span className="weakv2-map-icon"><Target size={20}/></span><h2>Focus map</h2></div></header>
          {mapTopics.length?<><svg className="weakv2-map" viewBox="0 0 320 210" role="img" aria-label="Interactive map of topics to revisit"><g stroke="#39316F" strokeWidth="2" fill="none" strokeDasharray="4 5"><path d="M66 72 184 105 257 48M184 105 134 163"/><circle cx="257" cy="48" r="15"/><circle cx="43" cy="169" r="13"/><circle cx="134" cy="188" r="11"/></g>{mapTopics.map((t:any,index:number)=>{const [cx,cy]=mapPoints[index];const rate=topicRate(t.accuracy);const radius=rate===null?30:26+(1-rate)*12;const fill=rateColor(rate);const label=topicInitials(String(t.topic));const pct=rate===null?'—':`${Math.round(rate*100)}%`;return <g key={`${t.topic}-${index}`} className={`weakv2-bubble ${selectedTopicIndex===index?"is-selected":""}`} role="button" tabIndex={0} aria-pressed={selectedTopicIndex===index} aria-label={`Jump to ${t.topic}`} onClick={()=>jumpToTopic(index)} onKeyDown={(e:any)=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();jumpToTopic(index)}}}><circle cx={cx} cy={cy} r={radius} fill={fill} fillOpacity=".94"/><text x={cx} y={cy-2} textAnchor="middle" className="weakv2-bubble-label">{label}</text><text x={cx} y={cy+13} textAnchor="middle" className="weakv2-bubble-pct">{pct}</text></g>})}</svg><p className="weakv2-caption">Bubbles use real topic accuracy. Select a bubble to jump to its card.</p></>:<div className="weakv2-map-empty"><Target size={25}/><p>Your focus map appears after weak topics are identified.</p></div>}
        </section>

        <section className="weakv2-panel weakv2-evidence"><header className="weakv2-panel-head"><div className="weakv2-panel-title"><span className="weakv2-evidence-icon"><RefreshCw size={16}/></span><h2>How strong is the signal?</h2></div></header><div className="weakv2-steps">{['Early signal','Repeated','Confirmed'].map((label,index)=><div key={label} className={`weakv2-step ${evidenceLevel>=index+1?'is-active':''}`}><span>{index===0?<CircleHelp size={14}/>:index===1?<RefreshCw size={14}/>:<CheckCircle2 size={14}/>}</span><b>{label}</b></div>)}</div><p className="weakv2-caption">{evidenceText}</p><p className="weakv2-disclaimer">A simple attempt-count guide—not a guarantee of mastery.</p></section>

        <section className="weakv2-tip"><Lightbulb size={17}/><div><b>Make each attempt count</b><p>Revise the idea, explain it from memory, then take another quiz. Repeated results help distinguish a pattern from a single miss.</p></div></section>
      </aside>
    </div>
  </div>;
}

function Workspace({token,courseId,courses,setCourses,setCourseId,notify}:any){const [sources,setSources]=useState<any[]>([]);const [chats,setChats]=useState<any[]>([]);const [name,setName]=useState('');const [description,setDescription]=useState('');const [creating,setCreating]=useState(false);const [uploading,setUploading]=useState(false);const [uploadJobs,setUploadJobs]=useState<any[]>([]);const [deletingSource,setDeletingSource]=useState<number|null>(null);const [err,setErr]=useState('');const refresh=async()=>{const nextSources=await request(`/api/courses/${courseId}/sources`,token);setSources(nextSources||[]);const nextChats=await request(`/api/courses/${courseId}/chats`,token);setChats(nextChats||[]);const nextJobs=await request(`/api/courses/${courseId}/upload-jobs`,token);setUploadJobs(nextJobs.jobs||[])};useEffect(()=>{if(courseId)refresh().catch((e:any)=>setErr(e.message))},[courseId,token]);const hasActiveUploadJobs=uploadJobs.some((j:any)=>j.status==='queued'||j.status==='processing');useEffect(()=>{if(!courseId||!hasActiveUploadJobs)return;const timer=window.setInterval(async()=>{try{const nextJobs=await request(`/api/courses/${courseId}/upload-jobs`,token);const next=nextJobs.jobs||[];setUploadJobs(next);const nextSources=await request(`/api/courses/${courseId}/sources`,token);setSources(nextSources||[])}catch(e:any){setErr(e.message)}},4000);return()=>window.clearInterval(timer)},[courseId,token,hasActiveUploadJobs]);async function upload(file?:File){if(!file)return;if(!courseId){setErr('Create a course before uploading a PDF.');return}setUploading(true);setErr('');const fd=new FormData();fd.append('file',file);try{const d=await request(`/api/courses/${courseId}/upload`,token,{method:'POST',body:fd});await refresh();if(d.status==='already_indexed'||d.duplicate&& !d.job_id){notify(`${d.filename} is already indexed · ${d.chunks} chunks`)}else if(d.job_id){notify(`Indexing started for ${d.filename}. You can continue working while it processes.`)}else{notify(`Upload accepted for ${d.filename}`)}}catch(e:any){setErr(e.message)}finally{setUploading(false)}}async function removeSource(source:any){if(!window.confirm(`Delete "${source.filename}" and remove its indexed text from this course?`))return;setDeletingSource(source.id);setErr('');try{await request(`/api/courses/${courseId}/sources/${source.id}`,token,{method:'DELETE'});notify(`Deleted ${source.filename}`);refresh()}catch(e:any){setErr(e.message)}finally{setDeletingSource(null)}}async function create(){if(!name.trim())return;setCreating(true);try{const c=await request('/api/courses',token,{method:'POST',body:JSON.stringify({name,description})});setCourses((x:Course[])=>[...x,c]);setCourseId(c.id);setName('');setDescription('');notify('Course created')}catch(e:any){setErr(e.message)}finally{setCreating(false)}}return <div className="cg-workspace-redesign">
<section className="cg-ws-hero">
  <svg className="cg-ws-network" viewBox="0 0 900 200" preserveAspectRatio="xMidYMid slice" aria-hidden="true"><g stroke="#b8afff" strokeOpacity=".42" fill="none"><path d="M70 40 200 110 150 180M200 110 360 50 470 140 360 190M470 140 620 50 760 130 860 40"/><path d="M360 50 620 50M470 140 760 130"/></g><g><circle cx="70" cy="40" r="5" fill="#b8afff"/><circle cx="200" cy="110" r="7" fill="#5eead4"/><circle cx="360" cy="50" r="6" fill="#b8afff"/><circle cx="470" cy="140" r="8" fill="#ffc86b"/><circle cx="620" cy="50" r="5" fill="#5eead4"/><circle cx="760" cy="130" r="6" fill="#b8afff"/></g></svg>
  <div className="cg-ws-hero-copy"><div className="cg-ws-eyebrow">COURSE WORKSPACE</div><h1>Your course, organised.</h1><p>Courses, PDFs and past chats in one place.</p></div>
  <div className="cg-ws-thinking" aria-hidden="true"><svg className="cg-ws-person" viewBox="0 0 120 132" fill="none"><path d="M12 132C12 102 34 90 60 90s48 12 48 42z" fill="#6c5ce7"/><rect x="53" y="76" width="14" height="17" rx="5" fill="#e8b98f"/><ellipse cx="60" cy="52" rx="22" ry="26" fill="#f2c9a5"/><path d="M37 52c-4-24 12-32 25-31 17 1 24 14 21 31-5-12-15-16-27-15-9 1-15 6-19 15z" fill="#4a3fb0"/><path d="M47 46q5-3 10 0M64 44q5-3 10 0" stroke="#2a2166" strokeWidth="2" strokeLinecap="round"/><circle cx="54" cy="52" r="2.6" fill="#120f2e"/><circle cx="71" cy="50" r="2.6" fill="#120f2e"/><path d="M55 66q5-2 9 0" stroke="#9a5b4a" strokeWidth="2" strokeLinecap="round"/></svg><div className="cg-ws-bubble"><b>Ask yourself</b>Which chapter will you add first?</div></div>
</section>
<div className="cg-ws-metrics">
  <div className="cg-ws-metric"><div className="cg-ws-metric-icon"><LibraryBig size={18}/></div><div><strong>{courses.length.toLocaleString()}</strong><span>Courses</span></div></div>
  <div className="cg-ws-metric"><div className="cg-ws-metric-icon"><FileText size={18}/></div><div><strong>{sources.length.toLocaleString()}</strong><span>PDFs</span></div></div>
  <div className="cg-ws-metric"><div className="cg-ws-metric-icon"><Workflow size={18}/></div><div><strong>{sources.reduce((sum:number, source:any)=>sum+(Number(source.chunks)||0),0).toLocaleString()}</strong><span>Text chunks</span></div></div>
  <div className="cg-ws-metric"><div className="cg-ws-metric-icon"><MessageCircle size={18}/></div><div><strong>{chats.length.toLocaleString()}</strong><span>Conversations</span></div></div>
</div>
<div className="cg-ws-content"><div className="workspace-grid"><div className="panel"><div className="panel-head"><div><h3>Your courses</h3><p>Each course has its own source collection.</p></div><LibraryBig size={19} className="subtle-icon"/></div><div className="course-list">{courses.map((c:Course)=><button className={`course-card ${courseId===c.id?'current':''}`} key={c.id} onClick={()=>setCourseId(c.id)}><div className="course-icon"><BookOpen size={19}/></div><div><b>{c.name}</b><small>{c.description||'Course workspace'}</small></div>{courseId===c.id&&<CheckCircle2 size={17}/>}</button>)}</div><div className="create-course"><h4><Plus size={16}/> Create a course</h4><input value={name} onChange={e=>setName(e.target.value)} placeholder="Course name"/><input value={description} onChange={e=>setDescription(e.target.value)} placeholder="Description (optional)"/><button className="secondary full" disabled={!name.trim()||creating} onClick={create}>{creating?'Creating…':'Add course'}</button></div></div><div className="panel materials-panel"><div className="panel-head"><div><h3>Course materials</h3><p>PDFs indexed for retrieval</p></div><span className="count-badge">{sources.length}</span></div>{courseId?<label className="upload-drop"><input type="file" accept="application/pdf,.pdf" onChange={e=>{upload(e.target.files?.[0]);e.currentTarget.value=''}} disabled={uploading} hidden/><div className="upload-icon"><Upload size={22}/></div><b>{uploading?'Processing PDF…':'Upload course PDF'}</b><p>PDF only · up to 35 MB</p><span className="secondary small">Choose file</span></label>:<p className="muted small-note">Create your first course before uploading course materials.</p>}{uploadJobs.slice(0,5).map((j:any)=><div className="small-note" key={j.id} role="status"><b>{j.filename}</b> · {j.status==='succeeded'?'Indexed':j.status==='failed'?`Failed: ${j.error||'Upload failed'}`:j.stage||'Queued for indexing'}</div>)}{err&&<div className="alert error">{err}</div>}<div className="source-list">{sources.map(s=><div className="material-row" key={s.id}><div className="pdf-icon"><FileText size={19}/></div><div><b>{s.filename}</b><small>{s.chunks} text chunks indexed</small></div><button className="text-button danger-text" disabled={deletingSource===s.id} onClick={()=>removeSource(s)} title={`Delete ${s.filename}`}><Trash2 size={14}/>{deletingSource===s.id?'Deleting…':'Delete'}</button></div>)}{!sources.length&&<p className="muted small-note">No PDFs yet. Upload course material to enable grounded tutoring.</p>}</div></div></div><div className="panel chats-panel"><div className="panel-head"><div><h3>Recent conversations</h3><p>Chat history for the selected course</p></div><MessageCircle size={19} className="subtle-icon"/></div>{chats.length?chats.map(c=><div className="conversation-row" key={c.id}><MessageCircle size={16}/><div><b>{c.title}</b><small>{new Date(c.updated_at*1000).toLocaleString()}</small></div></div>):<p className="muted">No conversations in this course yet.</p>}</div></div></div>}
function Saved({token,courseId,notify,setPage}:any){
  const [items,setItems]=useState<any[]>([]);
  const [err,setErr]=useState('');
  const [selected,setSelected]=useState<any>(null);
  const [filter,setFilter]=useState('all');
  const [query,setQuery]=useState('');
  const [starred,setStarred]=useState<number[]>([]);
  const [previewEmpty,setPreviewEmpty]=useState(false);
  const [loading,setLoading]=useState(true);
  const [imageUrls,setImageUrls]=useState<Record<number,string>>({});
  const starKey=`cg-saved-visual-stars:${courseId}`;

  const load=async()=>{
    if(!courseId){setItems([]);setLoading(false);return}
    setLoading(true);
    try{
      const rows=await request(`/api/courses/${courseId}/visualizations`,token);
      setItems(Array.isArray(rows)?rows:[]);
      setErr('');
    }catch(e:any){setErr(e.message||'Could not load saved visuals');}
    finally{setLoading(false)}
  };
  useEffect(()=>{setPreviewEmpty(false);setSelected(null);void load()},[courseId,token]);
  useEffect(()=>{
    try{
      const raw=JSON.parse(localStorage.getItem(starKey)||'[]');
      setStarred(Array.isArray(raw)?raw.map(Number).filter(Number.isFinite):[]);
    }catch{setStarred([])}
  },[courseId]);
  useEffect(()=>{
    let alive=true;
    const made:string[]=[];
    setImageUrls({});
    const fetchImages=async()=>{
      const imageItems=items.filter((x:any)=>x.file_path&&!String(x.source_text||'').trim());
      await Promise.all(imageItems.map(async(x:any)=>{
        try{
          const r=await fetch(`/api/courses/${courseId}/visualizations/${x.id}/content`,{headers:{Authorization:`Bearer ${token}`}});
          if(!r.ok)return;
          const url=URL.createObjectURL(await r.blob());made.push(url);
          if(alive)setImageUrls((prev:any)=>({...prev,[Number(x.id)]:url}));
        }catch{/* A missing legacy file should not prevent the rest of the library from rendering. */}
      }));
    };
    void fetchImages();
    return()=>{alive=false;made.forEach(URL.revokeObjectURL)};
  },[items,courseId,token]);

  function kindOf(x:any){
    const k=String(x.kind||'').toLowerCase();
    const clues=`${k} ${x.title||''} ${x.query||''}`.toLowerCase();
    if(k.includes('chart')||/\b(chart|plot|curve|regression|scatter)\b/.test(clues))return 'chart';
    if(k.includes('flow')||/\b(rag flow|workflow|process flow)\b/.test(clues))return 'flow';
    return 'diagram';
  }
  const categoryLabel=(x:any)=>kindOf(x)==='chart'?'Chart':kindOf(x)==='flow'?'Flow':'Diagram';
  const categoryIcon=(x:any)=>kindOf(x)==='chart'?<ChartNoAxesCombined size={14}/>:kindOf(x)==='flow'?<Workflow size={14}/>:<Workflow size={14}/>;
  const filtered=items.filter((x:any)=>{
    const matchType=filter==='all'||(filter==='star'?starred.includes(Number(x.id)):kindOf(x)===filter);
    const hay=`${x.title||''} ${x.query||''} ${x.kind||''}`.toLowerCase();
    return matchType&&hay.includes(query.trim().toLowerCase());
  });
  const chartCount=items.filter((x:any)=>kindOf(x)==='chart').length;
  const diagramFlowCount=items.length-chartCount;
  const starCount=items.filter((x:any)=>starred.includes(Number(x.id))).length;

  function toggleStar(id:number){
    const next=starred.includes(id)?starred.filter(x=>x!==id):[...starred,id];
    setStarred(next);
    try{localStorage.setItem(starKey,JSON.stringify(next))}catch{/* Star state still works for this session if storage is unavailable. */}
  }
  async function remove(id:number){
    if(!window.confirm('Delete this saved visual? This cannot be undone.'))return;
    try{
      await request(`/api/visualizations/${id}`,token,{method:'DELETE'});
      if(Number(selected?.id)===id)setSelected(null);
      const nextStars=starred.filter(x=>x!==id);setStarred(nextStars);
      try{localStorage.setItem(starKey,JSON.stringify(nextStars))}catch{}
      await load();notify('Saved visual deleted');
    }catch(e:any){setErr(e.message||'Could not delete this visual')}
  }
  function askTutor(x:any){
    const prompt=`Please explain this saved visualization: ${x.title||'Saved visual'}\nOriginal question: ${x.query||'Not recorded'}\nVisual type: ${categoryLabel(x)}. Explain what it shows and how to interpret it.`;
    try{localStorage.setItem('cg-next-tutor-prompt',prompt)}catch{}
    setSelected(null);setPage('tutor');notify('Your question is ready in Socratic Tutor');
  }
  async function download(x:any){
    try{
      let blob:Blob;
      let extension='txt';
      if(x.file_path&&!String(x.source_text||'').trim()){
        const r=await fetch(`/api/courses/${courseId}/visualizations/${x.id}/content?download=1`,{headers:{Authorization:`Bearer ${token}`}});
        if(!r.ok)throw new Error(`Download failed (${r.status})`);
        blob=await r.blob();extension='png';
      }else{
        const content=String(x.source_text||x.query||x.title||'');
        blob=new Blob([content],{type:'text/plain;charset=utf-8'});
        extension=kindOf(x)==='diagram'||kindOf(x)==='flow'?'mmd':'txt';
      }
      const url=URL.createObjectURL(blob);const a=document.createElement('a');
      const safe=String(x.title||'saved-visual').replace(/[^a-z0-9_-]+/gi,'-').replace(/^-+|-+$/g,'').slice(0,70)||'saved-visual';
      a.href=url;a.download=`${safe}.${extension}`;document.body.appendChild(a);a.click();a.remove();URL.revokeObjectURL(url);
      notify('Download started');
    }catch(e:any){setErr(e.message||'Could not download this visual')}
  }
  function renderVisual(x:any,large=false){
    const image=imageUrls[Number(x.id)];
    if(image)return <img className={large?'sv2-image sv2-image-large':'sv2-image'} src={image} alt={x.title||'Saved visualization'}/>;
    const source=String(x.source_text||'').trim();
    if(source&&/(^|\n)\s*(flowchart|graph\s+(TD|LR|RL|BT)|sequencediagram|classdiagram|statediagram|erdiagram|mindmap|journey|gantt|pie\b|xychart|quadrantchart)/i.test(source))return <div className={large?'sv2-mermaid sv2-mermaid-large':'sv2-mermaid'}><MermaidDiagram source={source}/></div>;
    if(source)return <pre className={large?'sv2-source sv2-source-large':'sv2-source'}>{source}</pre>;
    return <div className={large?'sv2-preview-fallback sv2-preview-fallback-large':'sv2-preview-fallback'}><Workflow size={large?42:30}/><b>{categoryLabel(x)}</b><span>{x.query||'Preview not available for this saved item.'}</span></div>;
  }
  const showEmpty=previewEmpty||(!loading&&items.length===0);

  return <div className="sv2">
    <section className="sv2-hero">
      <svg className="sv2-hero-lines" viewBox="0 0 900 200" preserveAspectRatio="xMidYMid slice" aria-hidden="true"><g stroke="#B8AFFF" strokeOpacity=".32" fill="none"><path d="M70 40 200 110 150 180M200 110 360 50 470 140 360 190M470 140 620 50M620 50 760 130 860 40"/></g><g><circle cx="70" cy="40" r="5" fill="#B8AFFF"/><circle cx="200" cy="110" r="7" fill="#5EEAD4"/><circle cx="360" cy="50" r="6" fill="#B8AFFF"/><circle cx="470" cy="140" r="8" fill="#FFC86B"/><circle cx="620" cy="50" r="5" fill="#5EEAD4"/><circle cx="760" cy="130" r="6" fill="#B8AFFF"/></g></svg>
      <div className="sv2-hero-copy"><span className="sv2-eyebrow">YOUR PERSONAL LIBRARY</span><h1>Your visual library.</h1><p>Diagrams you want to see again.</p></div>
      <div className="sv2-hero-art"><div className="sv2-orbit"><Workflow size={37}/></div><div className="sv2-bubble"><b>Ask yourself</b><span>Which idea is easier to see than to read?</span></div></div>
    </section>

    <div className="sv2-tiles">
      <div className="sv2-tile sv2-k1"><span className="sv2-tile-icon">▣</span><div><b>{previewEmpty?0:items.length.toLocaleString()}</b><span>Saved</span></div></div>
      <div className="sv2-tile sv2-k2"><span className="sv2-tile-icon"><Workflow size={18}/></span><div><b>{previewEmpty?0:diagramFlowCount.toLocaleString()}</b><span>Diagrams and flows</span></div></div>
      <div className="sv2-tile sv2-k3"><span className="sv2-tile-icon"><ChartNoAxesCombined size={18}/></span><div><b>{previewEmpty?0:chartCount.toLocaleString()}</b><span>Charts</span></div></div>
      <div className="sv2-tile sv2-k4"><span className="sv2-tile-icon">☆</span><div><b>{previewEmpty?0:starCount.toLocaleString()}</b><span>Starred</span></div></div>
    </div>

    <div className="sv2-toolbar">
      {!previewEmpty&&<div className="sv2-filters" role="group" aria-label="Filter saved visuals">
        {[['all','All'],['diagram','Diagrams'],['chart','Charts'],['flow','Flows'],['star','Starred']].map(([value,label])=><button type="button" key={value} aria-pressed={filter===value} className={filter===value?'active':''} onClick={()=>setFilter(value)}>{value==='all'?<Bookmark size={14}/>:value==='chart'?<ChartNoAxesCombined size={14}/>:value==='star'?<span className="sv2-filter-star">☆</span>:<Workflow size={14}/>}{label}</button>)}
      </div>}
      {!previewEmpty&&<label className="sv2-search"><Search size={16}/><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search visuals" aria-label="Search visuals"/></label>}
      {items.length>0&&<button type="button" className="sv2-preview-toggle" onClick={()=>{setPreviewEmpty(v=>!v);setSelected(null)}}>{previewEmpty?'← Back to saved visuals':'Preview empty state'}</button>}
    </div>

    {err&&<div className="alert error sv2-error" role="alert">{err}<button type="button" onClick={()=>setErr('')}>Dismiss</button></div>}
    {loading?<div className="sv2-loading"><i/><i/><i/>Loading your saved visuals…</div>:showEmpty?<section className="sv2-empty">
      <div className="sv2-skeletons" aria-hidden="true"><div><i/><span/><span/></div><div><i/><span/><span/></div><div><i/><span/><span/></div></div>
      <div className="sv2-empty-mark"><Bookmark size={27}/></div><h2>Nothing saved yet</h2><p>Ask the tutor to draw something, then save it to build your visual library.</p>
      <div className="sv2-empty-actions"><button type="button" onClick={()=>askTutor({title:'Gradient descent',query:'Visualize gradient descent and explain why it moves opposite to the gradient.'})}><ChartNoAxesCombined size={17}/>Visualize gradient descent</button><button type="button" onClick={()=>askTutor({title:'Neural network',query:'Draw a neural network and explain its layers.'})}><Workflow size={17}/>Draw a neural network</button><button type="button" onClick={()=>askTutor({title:'RAG',query:'Show how retrieval-augmented generation (RAG) works.'})}><MessageCircle size={17}/>Show how RAG works</button></div>
      {previewEmpty&&items.length>0&&<small className="sv2-preview-note">This is a preview only. Your {items.length} saved item{items.length===1?'':'s'} remain safely stored.</small>}
    </section>:filtered.length===0?<div className="sv2-no-results"><Search size={24}/><b>No visuals match this view</b><p>Try another category or search term.</p><button type="button" onClick={()=>{setFilter('all');setQuery('')}}>Clear filters</button></div>:<div className="sv2-gallery">
      {filtered.map((x:any)=>{const k=kindOf(x);const isStarred=starred.includes(Number(x.id));return <article className={`sv2-card sv2-card-${k}`} key={x.id}>
        <div className="sv2-card-art"><button type="button" className="sv2-card-open" onClick={()=>setSelected(x)} aria-label={`Open ${x.title||'saved visual'}`}>{renderVisual(x)}</button><span className={`sv2-kind sv2-kind-${k}`}>{categoryIcon(x)}{categoryLabel(x)}</span><button type="button" className={`sv2-star ${isStarred?'is-starred':''}`} aria-pressed={isStarred} aria-label={isStarred?'Remove star':'Star visual'} onClick={()=>toggleStar(Number(x.id))}>{isStarred?'★':'☆'}</button></div>
        <div className="sv2-card-body"><button type="button" className="sv2-card-title" onClick={()=>setSelected(x)}>{x.title||'Untitled visualization'}</button><div className="sv2-card-meta"><span className="sv2-tag">{String(x.kind||k).replace(/[_-]+/g,' ')}</span><span className="sv2-date">{x.created_at?new Date(Number(x.created_at)*1000).toLocaleDateString(undefined,{month:'short',day:'numeric'}):'Saved'}</span></div><div className="sv2-card-actions"><button type="button" onClick={()=>setSelected(x)} aria-label="View visual"><Eye size={15}/></button><button type="button" onClick={()=>void download(x)} aria-label="Download visual"><Download size={15}/></button><button type="button" className="remove" onClick={()=>void remove(Number(x.id))} aria-label="Delete visual"><Trash2 size={15}/></button></div></div>
      </article>})}
    </div>}

    {selected&&<div className="sv2-modal-backdrop" role="presentation" onClick={()=>setSelected(null)}><section className="sv2-modal" role="dialog" aria-modal="true" aria-labelledby="sv2-modal-title" onClick={(e:any)=>e.stopPropagation()}>
      <div className="sv2-modal-head"><div><span className={`sv2-kind sv2-kind-${kindOf(selected)}`}>{categoryIcon(selected)}{categoryLabel(selected)}</span><h2 id="sv2-modal-title">{selected.title||'Saved visualization'}</h2><p>{selected.query||'No original question was saved.'}</p></div><button type="button" className="sv2-modal-close" onClick={()=>setSelected(null)} aria-label="Close preview">×</button></div>
      <div className="sv2-modal-visual">{renderVisual(selected,true)}</div>
      <div className="sv2-modal-actions"><button type="button" className="primary" onClick={()=>askTutor(selected)}><MessageCircle size={16}/>Ask the tutor about this</button><button type="button" className="secondary" onClick={()=>void download(selected)}><Download size={16}/>Download</button><button type="button" className="danger" onClick={()=>void remove(Number(selected.id))}><Trash2 size={16}/>Delete</button></div>
    </section></div>}
  </div>;
}

function Progress({token,courseId,setPage}:any){
  const [d,setD]=useState<any>(null);
  const [err,setErr]=useState('');
  const [activityFilter,setActivityFilter]=useState('all');
  const [showMore,setShowMore]=useState(false);
  const [selectedDate,setSelectedDate]=useState('');
  useEffect(()=>{
    let live=true;
    setErr('');
    setD(null);
    if(!courseId)return;
    request(`/api/courses/${courseId}/dashboard`,token)
      .then((value:any)=>{if(live)setD(value)})
      .catch((e:any)=>{if(live)setErr(e?.message||'Could not load learning progress.')});
    return ()=>{live=false};
  },[courseId,token]);

  const dateKey=(date:Date)=>`${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}`;
  const todayKey=dateKey(new Date());
  const activity7d:Array<any>=Array.isArray(d?.activity_7d)?d.activity_7d:[];
  const days=Array.from({length:7},(_,index)=>{
    const date=new Date();date.setHours(0,0,0,0);date.setDate(date.getDate()-(6-index));
    const key=dateKey(date);
    const rows=activity7d.filter((a:any)=>dateKey(new Date(Number(a.created_at)*1000))===key);
    return {key,date,label:date.toLocaleDateString(undefined,{weekday:'short'}),count:rows.length,
      questions:rows.filter((a:any)=>a.event_type==='question_asked').length,
      quizzes:rows.filter((a:any)=>a.event_type==='quiz_answered').length,
      revisions:rows.filter((a:any)=>a.event_type==='revision_generated').length};
  });
  const activeDay=days.find(day=>day.key===selectedDate)||days[6];
  const maxActivity=Math.max(1,...days.map(day=>day.count));
  const quiz=d?.quiz||{};
  const attempts=Number(quiz.attempts||0);
  const correct=Number(quiz.correct||0);
  const incorrect=Number(quiz.incorrect||0);
  const accuracy=attempts>0?Math.max(0,Math.min(1,Number(quiz.accuracy)||0)):0;
  const accuracyPct=Math.round(accuracy*100);
  const recent:Array<any>=Array.isArray(d?.recent)?d.recent:[];
  const matchesFilter=(item:any)=>activityFilter==='all'||
    (activityFilter==='q'&&item.event_type==='question_asked')||
    (activityFilter==='z'&&item.event_type==='quiz_answered')||
    (activityFilter==='r'&&item.event_type==='revision_generated');
  const filteredRecent=recent.filter(matchesFilter);
  const shownRecent=showMore?filteredRecent:filteredRecent.slice(0,6);
  const eventName=(type:string)=>({
    question_asked:'Question asked',quiz_answered:'Quiz answered',revision_generated:'Revision generated',
    study_plan_generated:'Study plan generated',material_uploaded:'PDF indexed',material_deleted:'PDF deleted',
    visualization_saved:'Visual saved'
  } as Record<string,string>)[type]||String(type||'Activity').replace(/_/g,' ').replace(/^\w/,s=>s.toUpperCase());
  const eventKind=(type:string)=>type==='question_asked'?'question':type==='quiz_answered'?'quiz':type==='revision_generated'?'revision':'other';

  return <div className="progressv3">
    <section className="pr-hero">
      <svg className="pr-hero-lines" viewBox="0 0 900 200" preserveAspectRatio="xMidYMid slice" aria-hidden="true"><g stroke="#B8AFFF" strokeOpacity=".35" fill="none"><path d="M70 40 200 110 150 180M200 110 360 50 470 140 360 190M470 140 620 50M620 50 760 130 860 40"/></g><g><circle cx="70" cy="40" r="5" fill="#B8AFFF"/><circle cx="200" cy="110" r="7" fill="#5EEAD4"/><circle cx="360" cy="50" r="6" fill="#B8AFFF"/><circle cx="470" cy="140" r="8" fill="#FFC86B"/><circle cx="620" cy="50" r="5" fill="#5EEAD4"/><circle cx="760" cy="130" r="6" fill="#B8AFFF"/></g></svg>
      <div className="pr-hero-copy"><span className="pr-eyebrow">LEARNING ANALYTICS</span><h1>See how you’re doing.</h1><p>Your activity and practice, shown honestly.</p></div>
      <div className="pr-think" aria-hidden="true">
        <svg className="pr-person" viewBox="0 0 120 132" fill="none"><path d="M12 132C12 102 34 90 60 90s48 12 48 42z" fill="#6C5CE7"/><rect x="53" y="76" width="14" height="17" rx="5" fill="#E8B98F"/><ellipse cx="60" cy="52" rx="22" ry="26" fill="#F2C9A5"/><path d="M37 52c-4-24 12-32 25-31 17 1 24 14 21 31-5-12-15-16-27-15-9 1-15 6-19 15z" fill="#4A3FB0"/><path d="M47 46q5-3 10 0M64 44q5-3 10 0" stroke="#2A2166" strokeWidth="2" strokeLinecap="round"/><circle cx="54" cy="52" r="2.6" fill="#120F2E"/><circle cx="71" cy="50" r="2.6" fill="#120F2E"/><path d="M55 66q5-2 9 0" stroke="#9A5B4A" strokeWidth="2" strokeLinecap="round"/><path d="M92 126 84 98 70 76" stroke="#6C5CE7" strokeWidth="14" strokeLinecap="round" strokeLinejoin="round"/><circle cx="68" cy="72" r="8" fill="#F2C9A5"/></svg>
        <div className="pr-bubble"><b>Ask yourself</b><p>What did you understand best this week?</p></div>
      </div>
    </section>

    <div className="pr-stats">
      <div className="pr-stat pr-stat-violet"><span className="pr-stat-icon"><MessageCircle size={18}/></span><div><strong>{d?Number(d.questions||0).toLocaleString():'—'}</strong><span>Questions asked</span></div></div>
      <div className="pr-stat pr-stat-teal"><span className="pr-stat-icon"><MessageCircle size={18}/></span><div><strong>{d?Number(d.chats||0).toLocaleString():'—'}</strong><span>Conversations</span></div></div>
      <div className="pr-stat pr-stat-amber"><span className="pr-stat-icon"><Workflow size={18}/></span><div><strong>{d?Number(d.visuals||0).toLocaleString():'—'}</strong><span>Visuals saved</span></div></div>
      <div className="pr-stat pr-stat-green"><span className="pr-stat-icon"><Target size={18}/></span><div><strong>{d&&attempts>0?`${accuracyPct}%`:'—'}</strong><span>Quiz accuracy</span></div></div>
    </div>

    {err&&<div className="pr-error" role="alert">{err}<button type="button" onClick={()=>{setD(null);setErr('');request(`/api/courses/${courseId}/dashboard`,token).then(setD).catch((e:any)=>setErr(e?.message||'Could not load learning progress.'))}}>Retry</button></div>}

    <div className="pr-layout">
      <section className="pr-card pr-week-card">
        <div className="pr-card-head"><span className="pr-card-icon pr-violet"><ChartNoAxesCombined size={17}/></span><div><h2>Last 7 days</h2><p>Recorded course activity by day</p></div></div>
        <div className="pr-bars" role="group" aria-label="Recorded activity for the last seven local calendar days">
          {days.map(day=><button type="button" key={day.key} className={`pr-day-bar ${day.key===todayKey?'is-today':''} ${day.key===activeDay.key?'is-selected':''}`} aria-pressed={day.key===activeDay.key} onClick={()=>setSelectedDate(day.key)} title={`${day.date.toLocaleDateString()}: ${day.count} recorded activities`}>
            <span className="pr-bar-count">{day.count}</span><span className="pr-bar-track"><i style={{height:`${day.count===0?5:Math.max(10,day.count/maxActivity*100)}%`}}/></span><span className="pr-day-label">{day.label}</span>
          </button>)}
        </div>
        <div className="pr-day-summary"><MessageCircle size={16}/><span><b>{activeDay.date.toLocaleDateString(undefined,{weekday:'short',month:'short',day:'numeric'})}{activeDay.key===todayKey?' (today)':''}:</b> {activeDay.count} recorded activit{activeDay.count===1?'y':'ies'} · {activeDay.questions} question{activeDay.questions===1?'':'s'} · {activeDay.quizzes} quiz answer{activeDay.quizzes===1?'':'s'} · {activeDay.revisions} revision{activeDay.revisions===1?'':'s'}</span></div>
      </section>

      <section className="pr-card pr-quiz-card">
        <div className="pr-card-head"><span className="pr-card-icon pr-green"><Target size={17}/></span><div><h2>Quiz accuracy</h2><p>Verified saved attempts only</p></div></div>
        <div className="pr-quiz-content">
          <div className="pr-ring-wrap"><svg viewBox="0 0 124 124" role="img" aria-label={`${accuracyPct}% accuracy across ${attempts} verified quiz attempts`}><circle className="pr-ring-track" cx="62" cy="62" r="50"/><circle className="pr-ring-value" cx="62" cy="62" r="50" strokeDasharray="314" strokeDashoffset={314-(314*accuracy)}/><text x="62" y="69" textAnchor="middle">{accuracyPct}%</text></svg></div>
          <div className="pr-quiz-breakdown"><div className="pr-result-positive"><CheckCircle2 size={24}/><div><strong>{correct}</strong><span>correct</span></div></div><div className="pr-result-review"><Target size={24}/><div><strong>{incorrect}</strong><span>incorrect · review</span></div></div></div>
        </div>
        <div className="pr-attempt-footer"><span>{attempts} verified attempt{attempts===1?'':'s'}</span>{Number(quiz.unverified_attempts||0)>0&&<span className="pr-unverified">{Number(quiz.unverified_attempts)} older/unverified excluded</span>}</div>
        {!attempts&&<p className="pr-no-attempts">No verified quiz attempts yet. Complete a quiz to see your accuracy here.</p>}
      </section>

      <section className="pr-card pr-timeline-card">
        <div className="pr-card-head"><span className="pr-card-icon pr-teal"><BookOpen size={17}/></span><div><h2>Learning activity</h2><p>Recent events recorded for this course</p></div><span className="pr-head-spacer"/><span className="pr-record-count">{filteredRecent.length}</span></div>
        <div className="pr-filters" role="group" aria-label="Filter learning activity">
          {[['all','All',''],['q','Questions','question'],['z','Quizzes','quiz'],['r','Revision','revision']].map(([id,label,tone])=><button type="button" key={id} aria-pressed={activityFilter===id} className={`pr-filter ${tone?`pr-filter-${tone}`:''}`} onClick={()=>{setActivityFilter(id);setShowMore(false)}}>{label}</button>)}
        </div>
        {!d?<div className="pr-timeline-empty">Loading your saved activity…</div>:!shownRecent.length?<div className="pr-timeline-empty">{activityFilter==='all'?'No recorded activity yet. Ask a course question or complete a quiz to begin.':'No events in this category yet.'}</div>:<div className="pr-timeline">
          {shownRecent.map((item:any,index:number)=><div className={`pr-event pr-event-${eventKind(item.event_type)}`} key={`${item.event_type}-${item.created_at}-${index}`}>
            <span className="pr-event-icon">{item.event_type==='quiz_answered'?<Target size={17}/>:item.event_type==='revision_generated'?<BookOpen size={17}/>:item.event_type==='question_asked'?<MessageCircle size={17}/>:item.event_type==='material_uploaded'?<FileText size={17}/>:<Workflow size={17}/>}</span>
            <div className="pr-event-body"><b>{eventName(item.event_type)}</b><small>{item.detail||'No additional detail recorded'}</small><span className="pr-event-time">{new Date(Number(item.created_at)*1000).toLocaleString()}</span></div>
          </div>)}
          {filteredRecent.length>6&&<button type="button" className="pr-more" onClick={()=>setShowMore(v=>!v)}>{showMore?'Show fewer':'Show more activity'}</button>}
        </div>}
      </section>

      <section className="pr-card pr-snapshot-card">
        <div className="pr-card-head"><span className="pr-card-icon pr-amber"><Lightbulb size={17}/></span><div><h2>Snapshot</h2><p>A quick view of recorded progress</p></div></div>
        <div className="pr-snapshot-row"><span className="pr-snapshot-icon pr-violet"><MessageCircle size={16}/></span><span>Questions asked</span><strong>{d?Number(d.questions||0).toLocaleString():'—'}</strong></div>
        <div className="pr-snapshot-row"><span className="pr-snapshot-icon pr-amber"><Target size={16}/></span><span>Verified quiz attempts</span><strong>{d?attempts.toLocaleString():'—'}</strong></div>
        <div className="pr-snapshot-row"><span className="pr-snapshot-icon pr-teal"><FileText size={16}/></span><span>Course PDFs</span><strong>{d?Number(d.sources||0).toLocaleString():'—'}</strong></div>
        <div className="pr-snapshot-row"><span className="pr-snapshot-icon pr-coral"><Target size={16}/></span><span>Weak topics found</span><strong>{d?Number(d.weak_topics?.length||0).toLocaleString():'—'}</strong></div>
        <button type="button" className="pr-revise-button" onClick={()=>setPage('weak')}><Target size={16}/> Review weak topics</button>
        <div className="pr-honesty-note"><ShieldCheck size={17}/><p><b>Activity isn’t mastery.</b> These numbers summarize recorded activity and verified quiz attempts; they do not prove mastery on their own.</p></div>
      </section>
    </div>
  </div>;
}

createRoot(document.getElementById('root')!).render(<App/>);
