(() => {
  const h = React.createElement;
  const { useEffect, useState } = React;
  const api = '/api/disease/';
  const getCookie = name => document.cookie.split('; ').find(v => v.startsWith(name + '='))?.split('=')[1] || '';

  async function request(path, options = {}) {
    const headers = options.body instanceof FormData ? {} : {'Content-Type': 'application/json'};
    if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(options.method)) headers['X-CSRFToken'] = getCookie('csrftoken');
    const response = await fetch(api + path, {...options, headers: {...headers, ...options.headers}, credentials: 'same-origin'});
    if (response.status === 204) return null;
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Something went wrong.');
    return data;
  }

  function Auth({onSignedIn}) {
    const [registering, setRegistering] = useState(false), [username, setUsername] = useState(''), [password, setPassword] = useState(''), [error, setError] = useState(''), [busy, setBusy] = useState(false);
    const [details, setDetails] = useState({full_name: '', email: '', mobile_number: '', district: 'Coimbatore', state: 'Tamil Nadu', language: 'English'});
    const authCopy = {
      English: {tagline:'Rooted in Tamil soil.', intro:'CropCure brings practical AI support to every field, inspired by Tamil Nadu’s living farming wisdom.', spirit:'In the spirit of G. Nammalvar: care for soil, seed, water, and every living thing.', register:'Farmer registration', login:'Farmer sign in', createTitle:'Start your farm journal', loginTitle:'Vanakkam, farmer', createLead:'Create your profile to save diagnoses and local guidance.', loginLead:'Sign in to continue caring for your crop.', fullName:'Full name', email:'Email address', mobile:'Mobile number', district:'District', state:'State', language:'Preferred language', username:'Username', password:'Password', waiting:'Please wait…', create:'Create my account', signIn:'Sign in', already:'Already registered?', new:'New to CropCure?', makeAccount:'Create an account'},
      'தமிழ்': {tagline:'தமிழ் மண்ணில் வேரூன்றியது.', intro:'தமிழ்நாட்டின் வாழும் வேளாண் அறிவால் ஊக்கமளிக்கப்பட்டு, ஒவ்வொரு வயலுக்கும் CropCure பயனுள்ள AI துணையை வழங்குகிறது.', spirit:'ஜி. நம்மாழ்வார் வழியில்: மண், விதை, நீர் மற்றும் ஒவ்வோர் உயிரையும் காப்போம்.', register:'விவசாயி பதிவு', login:'விவசாயி உள்நுழைவு', createTitle:'உங்கள் வயல் பதிவேட்டைத் தொடங்குங்கள்', loginTitle:'வணக்கம், விவசாயி', createLead:'நோயறிதல் மற்றும் உள்ளூர் வழிகாட்டலைச் சேமிக்க சுயவிவரத்தை உருவாக்குங்கள்.', loginLead:'பயிரைப் பராமரிக்க தொடர்ந்து உள்நுழையுங்கள்.', fullName:'முழுப் பெயர்', email:'மின்னஞ்சல் முகவரி', mobile:'கைபேசி எண்', district:'மாவட்டம்', state:'மாநிலம்', language:'விருப்ப மொழி', username:'பயனர்பெயர்', password:'கடவுச்சொல்', waiting:'காத்திருக்கவும்…', create:'என் கணக்கை உருவாக்கு', signIn:'உள்நுழை', already:'ஏற்கனவே பதிவு செய்துள்ளீர்களா?', new:'CropCure-க்கு புதியவரா?', makeAccount:'கணக்கை உருவாக்கு'},
      'हिन्दी': {tagline:'तमिल मिट्टी में जड़ें।', intro:'तमिलनाडु की जीवंत कृषि समझ से प्रेरित, CropCure हर खेत के लिए उपयोगी AI सहायता लाता है।', spirit:'जी. नम्मालवार की भावना में: मिट्टी, बीज, पानी और हर जीव की देखभाल करें।', register:'किसान पंजीकरण', login:'किसान साइन इन', createTitle:'अपनी खेत डायरी शुरू करें', loginTitle:'वणक्कम, किसान', createLead:'निदान और स्थानीय मार्गदर्शन सहेजने के लिए अपनी प्रोफ़ाइल बनाएं।', loginLead:'अपनी फसल की देखभाल जारी रखने के लिए साइन इन करें।', fullName:'पूरा नाम', email:'ईमेल पता', mobile:'मोबाइल नंबर', district:'जिला', state:'राज्य', language:'पसंदीदा भाषा', username:'उपयोगकर्ता नाम', password:'पासवर्ड', waiting:'कृपया प्रतीक्षा करें…', create:'मेरा खाता बनाएं', signIn:'साइन इन', already:'पहले से पंजीकृत हैं?', new:'CropCure में नए हैं?', makeAccount:'खाता बनाएं'}
    };
    const word = key => authCopy[details.language][key];
    const districts = ['Ariyalur', 'Chengalpattu', 'Chennai', 'Coimbatore', 'Cuddalore', 'Dindigul', 'Erode', 'Kancheepuram', 'Kanyakumari', 'Karur', 'Krishnagiri', 'Madurai', 'Mayiladuthurai', 'Nagapattinam', 'Namakkal', 'Nilgiris', 'Perambalur', 'Pudukkottai', 'Ramanathapuram', 'Ranipet', 'Salem', 'Sivaganga', 'Tenkasi', 'Thanjavur', 'Theni', 'Thoothukudi', 'Tiruchirappalli', 'Tirunelveli', 'Tirupathur', 'Tiruppur', 'Tiruvallur', 'Tiruvannamalai', 'Tiruvarur', 'Vellore', 'Viluppuram', 'Virudhunagar'];
    const update = field => event => setDetails({...details, [field]: event.target.value});
    async function submit(event) {
      event.preventDefault(); setBusy(true); setError('');
      try { const user = await request(`auth/${registering ? 'register' : 'login'}/`, {method: 'POST', body: JSON.stringify(registering ? {...details, username, password} : {username, password})}); onSignedIn(user); }
      catch (err) { setError(err.message); } finally { setBusy(false); }
    }
    const field = (label, key, props = {}) => h('label', null, label, h('input', {value: details[key], onChange: update(key), ...props}));
    const registrationFields = registering ? h(React.Fragment, null,
      field(word('fullName'), 'full_name', {required: true, autoComplete: 'name'}),
      field(word('email'), 'email', {type: 'email', required: true, autoComplete: 'email'}),
      field(word('mobile'), 'mobile_number', {type: 'tel', required: true, pattern: '[0-9]{10}', placeholder: '10-digit mobile number', autoComplete: 'tel'}),
      h('label', null, word('district'), h('select', {value: details.district, onChange: update('district')}, districts.map(district => h('option', {key: district}, district)))),
      h('label', null, word('state'), h('select', {value: details.state, onChange: update('state')}, h('option', null, 'Tamil Nadu'))),
      h('label', null, word('language'), h('select', {value: details.language, onChange: update('language')}, ['English', 'தமிழ்', 'हिन्दी'].map(language => h('option', {key: language}, language))))
    ) : null;
    return h('main', {className: 'heritage-auth'},
      h('section', {className: 'auth-legacy'}, h('div', {className: 'kolam-mark'}, '❖'), h('p', {className: 'tamil-script'}, 'விவசாயம் நம் வாழ்வாதாரம்'), h('h1', null, word('tagline')), h('p', null, word('intro')), h('div', {className: 'nammalvar-note'}, h('span', null, '🌾'), h('p', null, word('spirit')))),
      h('section', {className: 'auth-panel'}, h('div', {className: 'auth-topline'}, h('span', null, '🌿 CropCure AI'), h('select', {className: 'auth-language', value: details.language, onChange: update('language'), 'aria-label': word('language')}, ['English', 'தமிழ்', 'हिन्दी'].map(language => h('option', {key: language}, language)))), h('div', {className: 'eyebrow'}, registering ? word('register') : word('login')), h('h2', null, registering ? word('createTitle') : word('loginTitle')), h('p', null, registering ? word('createLead') : word('loginLead')), h('form', {className: 'form', onSubmit: submit}, registrationFields, h('label', null, word('username'), h('input', {required: true, minLength: 3, value: username, onChange: e => setUsername(e.target.value), autoComplete: 'username'})), h('label', null, word('password'), h('input', {required: true, minLength: 8, type: 'password', value: password, onChange: e => setPassword(e.target.value), autoComplete: registering ? 'new-password' : 'current-password'})), error && h('div', {className: 'notice error'}, error), h('button', {className: 'primary', disabled: busy}, busy ? word('waiting') : registering ? word('create') : word('signIn'))), h('p', {className: 'auth-switch'}, registering ? word('already') + ' ' : word('new') + ' ', h('button', {type: 'button', className: 'switch', onClick: () => setRegistering(!registering)}, registering ? word('signIn') : word('makeAccount'))))
    );
  }

  function Dashboard({username, onLogout}) {
    const [image, setImage] = useState(null), [preview, setPreview] = useState(''), [result, setResult] = useState(null), [history, setHistory] = useState([]), [message, setMessage] = useState(''), [busy, setBusy] = useState(false);
    const load = () => request('history/').then(setHistory).catch(err => setMessage(err.message));
    useEffect(load, []);
    useEffect(() => () => { if (preview) URL.revokeObjectURL(preview); }, [preview]);
    function chooseImage(event) { const selected = event.target.files[0]; setMessage(''); setResult(null); if (!selected) return; if (!selected.type.startsWith('image/')) { setImage(null); return setMessage('Please upload a valid image file.'); } if (preview) URL.revokeObjectURL(preview); setImage(selected); setPreview(URL.createObjectURL(selected)); }
    async function analyze(event) { event.preventDefault(); if (!image) return setMessage('Please select a leaf image.'); setBusy(true); setMessage(''); const form = new FormData(); form.append('image', image); try { const saved = await request('create/', {method: 'POST', body: form}); setResult(saved); setImage(null); load(); } catch (err) { setMessage(err.message); } finally { setBusy(false); } }
    const list = (title, entries) => entries?.length ? h('section', {className: 'guidance'}, h('h3', null, title), h('ul', null, entries.map((entry, index) => h('li', {key: index}, entry)))) : null;
    const rows = history.length ? history.map(item => h('div', {className: 'row', key: item.id}, h('strong', null, `${item.crop} — ${item.disease}`), h('span', null, item.status), h('span', {className: 'muted'}, new Date(item.created_at).toLocaleString()))) : h('p', null, 'No saved checks yet.');
    const formCard = h('section', {className: 'card'}, h('h2', null, 'Upload Leaf Image'), h('form', {className: 'form', onSubmit: analyze}, h('label', null, 'Choose image', h('input', {type: 'file', accept: 'image/*', onChange: chooseImage})), preview && h('img', {className: 'preview', src: preview, alt: 'Selected leaf preview'}), message && h('div', {className: 'notice error'}, message), h('button', {className: 'primary', disabled: busy}, busy ? 'Detecting disease…' : 'Detect Disease')), h('p', {className: 'tip'}, 'The preview is browser-only. The uploaded image is processed for prediction and is not stored.'));
    const resultCard = h('section', {className: 'card result'}, result ? h(React.Fragment, null, h('div', {className: 'eyebrow'}, 'Disease Detection Result'), h('h2', null, result.disease), h('dl', {className: 'details'}, h('dt', null, 'Crop'), h('dd', null, result.crop), h('dt', null, 'Status'), h('dd', null, result.status)), result.status === 'Low confidence' && h('div', {className: 'notice'}, 'The model is not sufficiently confident. Please upload a clearer leaf image.'), result.guidance_available ? h(React.Fragment, null, list('Symptoms', result.symptoms), list('Recommended solution', result.solution), list('Prevention', result.prevention)) : h('p', {className: 'notice'}, 'Disease guidance has not yet been configured for this model class.')) : h(React.Fragment, null, h('div', {className: 'eyebrow'}, 'Result'), h('h2', null, 'Your assessment will appear here'), h('p', null, 'Upload a clear, well-lit leaf photo to run the trained MobileNetV2 model.')));
    return h(React.Fragment, null, h('nav', {className: 'nav'}, h('div', {className: 'brand'}, 'Crop', h('span', null, 'Cure')), h('div', null, username, ' ', h('button', {onClick: onLogout}, 'Sign out'))), h('main', {className: 'shell'}, h('section', {className: 'dashboard-head'}, h('div', null, h('div', {className: 'eyebrow'}, 'Farm dashboard'), h('h1', null, 'Check a crop, act with care.'), h('p', null, 'Upload a leaf photo and record a preliminary field assessment.'))), h('div', {className: 'grid'}, formCard, resultCard), h('section', {className: 'card history'}, h('h2', null, 'Recent checks'), rows)));
  }

  function App() { const [user, setUser] = useState(null); useEffect(() => { request('auth/me/').then(data => setUser(data.username)).catch(() => {}); }, []); if (user) { window.location.replace('/home.html'); return null; } return h(Auth, {onSignedIn: setUser}); }
  ReactDOM.createRoot(document.getElementById('root')).render(h(App));
})();
