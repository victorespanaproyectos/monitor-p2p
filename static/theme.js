(()=>{
 const key='p2p-theme',root=document.documentElement;
 function stored(){try{return localStorage.getItem(key);}catch{return null;}}
 function apply(value){
  const theme=value==='dark'?'dark':'light';root.dataset.theme=theme;root.style.colorScheme=theme;
  for(const button of document.querySelectorAll('.theme-button'))button.setAttribute('aria-pressed',String(button.dataset.theme===theme));
 }
 apply(stored());
 function setup(){
  const header=document.querySelector('.header-inner');if(!header||document.getElementById('theme-control'))return;
  const control=document.createElement('div');control.id='theme-control';control.className='theme-control';control.setAttribute('role','group');control.setAttribute('aria-label','Elegir tema');
  const icons={
   light:'<circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M4.93 4.93l1.42 1.42m11.3 11.3 1.42 1.42M4.93 19.07l1.42-1.42m11.3-11.3 1.42-1.42"/>',
   dark:'<path d="M20.7 13.5A9 9 0 0 1 10.5 3.3 9 9 0 1 0 20.7 13.5Z"/>'
  };
  for(const [theme,label] of [['light','Modo claro'],['dark','Modo oscuro']]){
   const button=document.createElement('button');button.type='button';button.className='theme-button';button.dataset.theme=theme;button.title=label;button.setAttribute('aria-label',label);
   button.innerHTML='<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'+icons[theme]+'</svg>';
   button.addEventListener('click',()=>{apply(theme);try{localStorage.setItem(key,theme);}catch{}});control.append(button);
  }
  header.append(control);apply(stored());
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',setup,{once:true});else setup();
 window.addEventListener('storage',event=>{if(event.key===key)apply(event.newValue);});
})();
