import React, { useEffect, useRef, useState } from 'react';
import { api } from '../../api/client';
import { Scheme } from '../../api/types';
import {
  ArrowRight,
  HelpCircle,
  HeartHandshake,
  Eye,
  Scale,
  ShieldCheck,
  UserCheck,
  FileCheck2,
  Upload,
  Award,
  Users,
  Landmark,
  CheckCircle2,
  XCircle,
  IndianRupee,
  Clock,
  BookOpen,
  GraduationCap,
  Sparkles,
  ChevronDown,
} from 'lucide-react';

interface LandingProps {
  onGetStarted: () => void;
  onSignIn: () => void;
}

const inputClass =
  'w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:outline-none';
const fieldLabel = 'block text-xs font-semibold text-slate-700 mb-1';

/* ---------------------------- helpers ---------------------------- */

function useInView<T extends HTMLElement>(threshold = 0.15) {
  const ref = useRef<T>(null);
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          io.disconnect();
        }
      },
      { threshold },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [threshold]);
  return { ref, visible };
}

const Reveal: React.FC<{ delay?: number; className?: string; children: React.ReactNode }> = ({
  delay = 0,
  className = '',
  children,
}) => {
  const { ref, visible } = useInView<HTMLDivElement>();
  return (
    <div
      ref={ref}
      style={{ transitionDelay: `${delay}ms` }}
      className={`reveal ${visible ? 'is-visible' : ''} ${className}`}
    >
      {children}
    </div>
  );
};

const CountUp: React.FC<{ to: number; suffix?: string }> = ({ to, suffix = '' }) => {
  const { ref, visible } = useInView<HTMLSpanElement>(0.4);
  const [value, setValue] = useState(0);
  useEffect(() => {
    if (!visible) return;
    const start = performance.now();
    const duration = 1400;
    let raf = 0;
    const tick = (now: number) => {
      const progress = Math.min(1, (now - start) / duration);
      setValue(Math.round(to * (1 - Math.pow(1 - progress, 3))));
      if (progress < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [visible, to]);
  return (
    <span ref={ref}>
      {value.toLocaleString('en-IN')}
      {suffix}
    </span>
  );
};

/* ------------------------- hero ------------------------- */

const HERO_PHRASES = [
  'A scholarship should be earned by merit, not lost in paperwork.',
  'Five national ST schemes, one honest platform.',
  'Every claim is compared against the evidence.',
  'Every decision is recorded and replayable.',
];

const Typewriter: React.FC = () => {
  const [text, setText] = useState('');
  const [phraseIndex, setPhraseIndex] = useState(0);
  const [phase, setPhase] = useState<'typing' | 'pausing' | 'deleting'>('typing');

  useEffect(() => {
    const phrase = HERO_PHRASES[phraseIndex];
    const delay = phase === 'typing' ? 42 : phase === 'deleting' ? 20 : 1700;
    const timer = window.setTimeout(() => {
      if (phase === 'typing') {
        const next = phrase.slice(0, text.length + 1);
        setText(next);
        if (next === phrase) setPhase('pausing');
      } else if (phase === 'deleting') {
        const next = phrase.slice(0, text.length - 1);
        setText(next);
        if (next === '') {
          setPhraseIndex((phraseIndex + 1) % HERO_PHRASES.length);
          setPhase('typing');
        }
      } else {
        setPhase('deleting');
      }
    }, delay);
    return () => window.clearTimeout(timer);
  }, [text, phase, phraseIndex]);

  return (
    <span className="font-serif text-emerald-800" aria-live="polite">
      {text}
      <span className="inline-block w-0.5 h-5 ml-0.5 bg-emerald-700 align-middle animate-pulse" />
    </span>
  );
};

const VALUE_TICKS = [
  'Integrity',
  'Transparency',
  'Equity',
  'Dignity',
  'Access',
  'Accountability',
  'Trust',
  'Merit',
];

const ValueMarquee: React.FC = () => (
  <div className="relative overflow-hidden bg-blue-950 border-y border-blue-900 py-3 select-none">
    <div className="flex w-max gap-10 animate-marquee">
      {[...VALUE_TICKS, ...VALUE_TICKS, ...VALUE_TICKS, ...VALUE_TICKS].map((word, i) => (
        <span key={i} className="flex items-center gap-10 text-sm font-semibold tracking-wide text-amber-400/90 uppercase">
          <span>{word}</span>
          <span className="text-emerald-500">◆</span>
        </span>
      ))}
    </div>
  </div>
);

/* -------------------------- values -------------------------- */

const VALUES = [
  {
    icon: Scale,
    title: 'Equity',
    body: 'Merit and honest evidence decide — never the ability to navigate paperwork. One consistent set of rules for every applicant.',
  },
  {
    icon: ShieldCheck,
    title: 'Integrity',
    body: 'Every verification and every decision carries a written reason and the officer who made it. Nothing is changed invisibly.',
  },
  {
    icon: Eye,
    title: 'Transparency',
    body: 'The applicant sees the stage their application is in, and an auditor can replay the whole journey from submit to sanction.',
  },
  {
    icon: HeartHandshake,
    title: 'Dignity',
    body: 'Deficient does not mean dismissed. Missing evidence is named plainly, corrections are allowed, and withdrawal is a right.',
  },
];

const ValuesSection: React.FC = () => (
  <section id="values" className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 sm:py-20">
    <Reveal className="text-center max-w-2xl mx-auto mb-12">
      <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-blue-100 text-blue-900 border border-blue-200 uppercase tracking-wide">
        Arohan — الأس
      </span>
      <h2 className="text-2xl sm:text-3xl font-bold text-slate-950 mt-2">What we stand for</h2>
      <p className="text-sm text-slate-600 mt-2">
        The platform is named for <span className="font-semibold text-blue-900">arohan</span> — the climb. The scholar
        climbs; the system should never be the thing that stops them.
      </p>
    </Reveal>
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
      {VALUES.map((v, i) => (
        <Reveal key={v.title} delay={i * 90}>
          <div className="group bg-white rounded-xl border border-slate-200 shadow-sm hover:shadow-md transition-all hover:-translate-y-1 p-6 h-full">
            <div className="w-12 h-12 rounded-xl bg-blue-900 text-amber-400 flex items-center justify-center mb-4 shadow-sm">
              <v.icon className="w-6 h-6" />
            </div>
            <h3 className="text-base font-bold text-slate-900">{v.title}</h3>
            <p className="text-xs text-slate-600 mt-2 leading-relaxed">{v.body}</p>
          </div>
        </Reveal>
      ))}
    </div>
  </section>
);

/* -------------------------- goals -------------------------- */

const GOALS = {
  scholar: [
    'One application, not a different portal for every scheme',
    'Every stage of the journey visible from a single tracker',
    'Missing evidence told plainly, not silently rejected',
    'Right to withdraw while the application is still open',
    'Award and payment milestones tracked for the scholar',
  ],
  officer: [
    'One verification queue across all five schemes',
    'Declared data set side-by-side with extracted evidence',
    'Every verification and decision recorded with reasons',
    'A marks-based ranking aid that never overrules the human',
    'Complete per-scheme reports and a replayable audit trail',
  ],
};

const GoalsSection: React.FC = () => {
  const [audience, setAudience] = useState<'scholar' | 'officer'>('scholar');
  return (
    <section id="goals" className="bg-white border-y border-slate-200 py-16 sm:py-20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 grid grid-cols-1 lg:grid-cols-2 gap-10 items-center">
        <Reveal>
          <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-blue-100 text-blue-900 border border-blue-200 uppercase tracking-wide">
            Our Goal
          </span>
          <h2 className="text-2xl sm:text-3xl font-bold text-slate-950 mt-2 leading-snug">
            One mine from the first upload to the final sanction —<span className="text-emerald-800"> for every scholar</span> and
            <span className="text-blue-900"> every officer</span>.
          </h2>
          <p className="text-sm text-slate-600 mt-3 leading-relaxed">
            AROHAN-ST brings five MoTA scholarship and fellowship schemes into a single verifiable record: registration,
            application, evidence, review, decision, award and payment. It works for two people at a time — the student
            and the officer who owes them a fair, explainable decision.
          </p>
        </Reveal>

        <Reveal delay={120}>
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="flex rounded-t-xl border-b border-slate-200 bg-slate-50/70">
              <button
                onClick={() => setAudience('scholar')}
                className={`flex-1 flex items-center justify-center gap-2 py-3.5 text-xs font-semibold transition ${
                  audience === 'scholar' ? 'bg-white text-blue-900 shadow-inner border-r border-t-2 border-blue-900' : 'text-slate-500 hover:text-slate-700'
                }`}
              >
                <Users className="w-4 h-4" />
                For Scholars
              </button>
              <button
                onClick={() => setAudience('officer')}
                className={`flex-1 flex items-center justify-center gap-2 py-3.5 text-xs font-semibold transition ${
                  audience === 'officer' ? 'bg-white text-emerald-800 shadow-inner border-l border-t-2 border-emerald-700' : 'text-slate-500 hover:text-slate-700'
                }`}
              >
                <Landmark className="w-4 h-4" />
                For Officers
              </button>
            </div>
            <ul className="p-6 space-y-3">
              {GOALS[audience].map((item) => (
                <li key={item} className="flex items-start gap-3 text-sm text-slate-700">
                  <CheckCircle2
                    className={`w-5 h-5 mt-0.5 flex-shrink-0 ${audience === 'scholar' ? 'text-blue-700' : 'text-emerald-700'}`}
                  />
                  {item}
                </li>
              ))}
            </ul>
          </div>
        </Reveal>
      </div>
    </section>
  );
};

/* ---------------------- schemes explorer ---------------------- */

const SchemeDetail: React.FC<{ scheme: Scheme }> = ({ scheme }) => {
  const rules = scheme.config.eligibility_rules;
  const rows = [
    {
      icon: GraduationCap,
      label: 'Course level',
      value: scheme.degree_level,
    },
    {
      icon: IndianRupee,
      label: 'Income ceiling',
      value: rules.max_annual_income != null ? `≤ ₹${(rules.max_annual_income / 100000).toFixed(1)} Lakh / year` : 'No cap',
    },
    {
      icon: BookOpen,
      label: 'Min. qualifying marks',
      value: rules.min_qualifying_percentage != null ? `${rules.min_qualifying_percentage}% aggregate` : 'No fixed cutoff',
    },
    {
      icon: Clock,
      label: 'Age ceiling',
      value: rules.max_age != null ? `Up to ${rules.max_age} years on 1 July of the award year` : 'No fixed ceiling',
    },
    {
      icon: Sparkles,
      label: 'Financial assistance',
      value: scheme.config.stipend_amount,
    },
  ];

  return (
    <div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {rows.map((r) => (
          <div key={r.label} className="flex items-center justify-between gap-3 py-2.5 px-4 bg-slate-50/70 rounded-lg border border-slate-200/70">
            <span className="text-xs text-slate-500 flex items-center gap-2">
              <r.icon className="w-4 h-4 text-slate-400" />
              {r.label}
            </span>
            <span className="text-xs font-semibold text-slate-800 text-right">{r.value}</span>
          </div>
        ))}
        <div className="flex items-center justify-between gap-3 py-2.5 px-4 bg-slate-50/70 rounded-lg border border-slate-200/70 sm:col-span-2">
          <span className="text-xs text-slate-500 flex items-center gap-2">
            <HeartHandshake className="w-4 h-4 text-slate-400" />
            Target category
          </span>
          <span className="text-xs font-semibold text-slate-800 text-right">{rules.target_category}</span>
        </div>
      </div>

      <div className="mt-4">
        <div className="text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-2">
          Required verifiable documents ({scheme.config.required_documents?.length || 0})
        </div>
        <div className="flex flex-wrap gap-2">
          {scheme.config.required_documents?.map((doc) => (
            <span key={doc.id} className="text-[11px] px-2.5 py-1 rounded-full bg-blue-50 text-blue-900 border border-blue-100">
              {doc.name}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
};

const EligibilityCheck: React.FC<{ scheme: Scheme }> = ({ scheme }) => {
  const rules = scheme.config.eligibility_rules;
  const [isST, setIsST] = useState(false);
  const [age, setAge] = useState(24);
  const [income, setIncome] = useState(180000);
  const [marks, setMarks] = useState(65);

  const checks = [
    {
      label: 'Scheduled Tribe student',
      ok: isST,
      note: isST ? 'Confirmed by you — the ST certificate is the document an officer verifies.' : 'Only ST students are eligible under these schemes.',
    },
    {
      label: rules.max_age != null ? `Age up to ${rules.max_age} years` : 'Age check',
      ok: rules.max_age == null || age <= rules.max_age!,
      note: rules.max_age != null ? `Declared age ${age} years on 1 July of the award year.` : 'No fixed age ceiling configured for this scheme.',
    },
    {
      label: rules.max_annual_income != null ? 'Family income within ceiling' : 'Income check',
      ok: rules.max_annual_income == null || income <= rules.max_annual_income!,
      note:
        rules.max_annual_income != null
          ? `Declared ₹${(income / 100000).toFixed(2)} Lakh against a ₹${(rules.max_annual_income / 100000).toFixed(1)} Lakh ceiling.`
          : 'No income ceiling applies to this scheme.',
    },
    {
      label: rules.min_qualifying_percentage != null ? `At least ${rules.min_qualifying_percentage}% marks` : 'Marks check',
      ok: rules.min_qualifying_percentage == null || marks >= rules.min_qualifying_percentage!,
      note:
        rules.min_qualifying_percentage != null
          ? `Declared ${marks}% against a ${rules.min_qualifying_percentage}% requirement.`
          : 'No fixed cutoff configured — admission/merit still verified by the officer.',
    },
  ];
  const allPass = checks.every((c) => c.ok);

  return (
    <div className="mt-6 rounded-xl border border-blue-200 bg-blue-50/40 p-5">
      <div className="flex items-center gap-2 mb-4">
        <UserCheck className="w-5 h-5 text-blue-900" />
        <h4 className="text-sm font-bold text-slate-900">
          Instant pre-check for {scheme.code}
        </h4>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
        <label className="block col-span-1 sm:col-span-1 rounded-lg bg-white border border-slate-200 p-3 flex items-center gap-2.5 cursor-pointer hover:border-blue-300 transition">
          <input type="checkbox" checked={isST} onChange={(e) => setIsST(e.target.checked)} className="accent-blue-900 w-4 h-4" />
          <span className="text-xs font-semibold text-slate-700">I am an ST student</span>
        </label>
        <label className="block">
          <span className={fieldLabel}>Age (years)</span>
          <input type="number" min={10} max={60} value={age} onChange={(e) => setAge(Number(e.target.value))} className={inputClass} />
        </label>
        <label className="block">
          <span className={fieldLabel}>Family income (₹/year)</span>
          <input type="number" min={0} step={10000} value={income} onChange={(e) => setIncome(Number(e.target.value))} className={inputClass} />
        </label>
        <label className="block">
          <span className={fieldLabel}>Qualifying marks (%)</span>
          <input type="number" min={0} max={100} value={marks} onChange={(e) => setMarks(Number(e.target.value))} className={inputClass} />
        </label>
      </div>
      <div className="mt-4 space-y-2">
        {checks.map((c) => (
          <div key={c.label} className="flex items-start gap-2.5 text-xs">
            {c.ok ? (
              <CheckCircle2 className="w-4 h-4 mt-0.5 text-emerald-700 flex-shrink-0" />
            ) : (
              <XCircle className="w-4 h-4 mt-0.5 text-rose-600 flex-shrink-0" />
            )}
            <div>
              <span className={`font-semibold ${c.ok ? 'text-emerald-800' : 'text-rose-700'}`}>{c.label}</span>
              <span className="text-slate-600 block">{c.note}</span>
            </div>
          </div>
        ))}
        <div
          className={`mt-3 p-3 rounded-lg text-xs font-semibold ${
            allPass ? 'bg-emerald-100 text-emerald-900 border border-emerald-200' : 'bg-amber-50 text-amber-900 border border-amber-200'
          }`}
        >
          {allPass
            ? `Based on what you declared, ${scheme.code} looks open to you. Upload evidence and let an officer verify before applying for real.`
            : `${scheme.code} would need the items above addressed, or a scheme with different rules. The officer's verification of documents decides the outcome.`}
        </div>
        <p className="text-[10px] text-slate-500 italic">
          Informal pre-check from the published scheme rules only. It never approves or rejects — document verification
          and a recorded officer decision always come first.
        </p>
      </div>
    </div>
  );
};

const SchemesExplorer: React.FC = () => {
  const [schemes, setSchemes] = useState<Scheme[]>([]);
  const [active, setActive] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    api
      .getSchemes()
      .then((data) => {
        if (!mounted) return;
        setSchemes(data);
        setActive(data[0]?.code ?? null);
      })
      .catch((err: Error) => mounted && setError(err.message || 'Schemes could not be loaded.'))
      .finally(() => mounted && setLoading(false));
    return () => {
      mounted = false;
    };
  }, []);

  const activeScheme = schemes.find((s) => s.code === active) ?? null;

  return (
    <section id="schemes" className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 sm:py-20">
      <Reveal className="text-center max-w-2xl mx-auto mb-10">
        <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-blue-100 text-blue-900 border border-blue-200 uppercase tracking-wide">
          What We Do
        </span>
        <h2 className="text-2xl sm:text-3xl font-bold text-slate-950 mt-2">Five schemes, one platform</h2>
        <p className="text-sm text-slate-600 mt-2">
          Explore the national MoTA schemes we operationalise — or pre-check your eligibility from the published rules.
        </p>
      </Reveal>

      {loading ? (
        <div className="flex flex-col items-center justify-center py-16 text-slate-500">
          <div className="inline-block animate-spin rounded-full h-9 w-9 border-4 border-blue-900 border-r-transparent mb-3" />
          <p className="text-xs">Loading the MoTA scheme catalogue…</p>
        </div>
      ) : error ? (
        <div className="max-w-2xl mx-auto p-4 bg-rose-50 border border-rose-200 rounded-lg text-rose-800 text-sm flex items-start gap-3">
          <XCircle className="w-5 h-5 text-rose-600 flex-shrink-0 mt-0.5" />
          <div>
            <div className="font-semibold">Scheme catalogue unavailable</div>
            <p className="text-xs text-rose-700 mt-1">{error}</p>
            <p className="text-xs text-slate-500 mt-1">The catalogue is loaded live from the API, so the landing stays honest about the platform.</p>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-8">
          <div className="lg:col-span-2 space-y-2.5">
            {schemes.map((s, i) => {
              const isActive = s.code === active;
              return (
                <Reveal key={s.code} delay={i * 60}>
                  <button
                    onClick={() => setActive(s.code)}
                    className={`w-full text-left p-4 rounded-xl border transition-all flex items-center gap-3.5 ${
                      isActive
                        ? 'bg-blue-950 border-blue-900 shadow-md text-white'
                        : 'bg-white border-slate-200 shadow-sm hover:shadow-md hover:border-blue-200 text-slate-700'
                    }`}
                  >
                    <div
                      className={`w-11 h-11 rounded-lg flex items-center justify-center shrink-0 ${
                        isActive ? 'bg-blue-800 text-amber-400' : 'bg-slate-100 text-blue-900'
                      }`}
                    >
                      <GraduationCap className={`w-5 h-5 ${isActive ? 'text-amber-400' : ''}`} />
                    </div>
                    <div className="min-w-0">
                      <div className={`text-[10px] font-bold tracking-wide ${isActive ? 'text-blue-300' : 'text-slate-400'}`}>
                        {s.config.external_code ? `${s.code} · ID ${s.config.external_code}` : `CODE ${s.code}`}
                      </div>
                      <div className="text-sm font-bold truncate">{s.name}</div>
                      <div className={`text-[11px] ${isActive ? 'text-blue-200' : 'text-slate-500'}`}>{s.degree_level}</div>
                    </div>
                  </button>
                </Reveal>
              );
            })}
          </div>

          <div className="lg:col-span-3">
            {activeScheme && (
              <Reveal key={activeScheme.code}>
                <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 sm:p-8">
                  <div className="flex items-start justify-between gap-4 mb-4">
                    <div>
                      <div className="text-[10px] font-bold text-blue-700 tracking-wide">{activeScheme.config.external_code ? `ID ${activeScheme.config.external_code}` : activeScheme.code}</div>
                      <h3 className="text-lg font-bold text-slate-900 leading-snug">{activeScheme.name}</h3>
                    </div>
                    <span className="text-xs font-bold px-2.5 py-1 rounded bg-slate-100 text-slate-700 border border-slate-200 whitespace-nowrap">
                      {activeScheme.config.registry_metadata?.delivery_type} · {activeScheme.config.registry_metadata?.scheme_type}
                    </span>
                  </div>
                  <p className="text-sm text-slate-600 mb-5 leading-relaxed">{activeScheme.description}</p>
                  <SchemeDetail scheme={activeScheme} />
                  <EligibilityCheck scheme={activeScheme} />
                </div>
              </Reveal>
            )}
          </div>
        </div>
      )}
    </section>
  );
};

/* ------------------------- pathway ------------------------- */

const STEPS = [
  {
    icon: UserCheck,
    title: 'Register',
    who: 'Scholar',
    summary: 'A real account, hashed password, no shared codes.',
    detail:
      'Applicants create their own account. The server enforces password strength, refuses duplicates, and decides the role — the email address never implies one.',
  },
  {
    icon: FileCheck2,
    title: 'Apply',
    who: 'Scholar',
    summary: 'A dynamic form per scheme, filled honestly.',
    detail:
      'The form and document list are generated from the scheme JSON. What the applicant declares is recorded verbatim and later compared with the evidence.',
  },
  {
    icon: Upload,
    title: 'Upload evidence',
    who: 'Scholar',
    summary: 'Certificates into GridFS, text extracted on arrival.',
    detail:
      'Documents go straight into MongoDB GridFS — never a server folder — through a private route owned by the applicant. Text is extracted and fields pulled out for the officer.',
  },
  {
    icon: ShieldCheck,
    title: 'Officer verification',
    who: 'Officer',
    summary: 'Document by document, each with a written reason.',
    detail:
      'One queue across all schemes. Declared values sit beside extracted values and the configured rules. Every verification and every reason lands in the audit trail.',
  },
  {
    icon: Award,
    title: 'Select, award, track',
    who: 'Both',
    summary: 'Selection gate, sanction, payments, scholar visibility.',
    detail:
      'Selection requires verified documents and passing rules; approval requires a recorded selection. The award and its payments are tracked, and the scholar watches the whole journey.',
  },
];

const PathwaySection: React.FC = () => {
  const [open, setOpen] = useState<number>(0);
  return (
    <section id="how" className="bg-white border-y border-slate-200 py-16 sm:py-20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <Reveal className="text-center max-w-2xl mx-auto mb-12">
          <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-emerald-100 text-emerald-900 border border-emerald-200 uppercase tracking-wide">
            How We Support
          </span>
          <h2 className="text-2xl sm:text-3xl font-bold text-slate-950 mt-2">The climb, stage by stage</h2>
          <p className="text-sm text-slate-600 mt-2">Click any stage to see what happens there — and who it serves.</p>
        </Reveal>

        <div className="grid grid-cols-1 md:grid-cols-5 gap-3 mb-6">
          {STEPS.map((step, i) => {
            const active = open === i;
            return (
              <Reveal key={step.title} delay={i * 70}>
                <button
                  onClick={() => setOpen(active ? -1 : i)}
                  className={`w-full text-left p-4 rounded-xl border transition-all ${
                    active
                      ? 'bg-blue-950 border-blue-900 text-white shadow-md'
                      : 'bg-white border-slate-200 shadow-sm hover:shadow-md text-slate-700'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div
                      className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                        active ? 'bg-blue-800 text-amber-400' : 'bg-slate-100 text-blue-900'
                      }`}
                    >
                      <step.icon className="w-5 h-5" />
                    </div>
                    <span className={`text-[10px] font-bold ${active ? 'text-blue-300' : 'text-slate-400'}`}>0{i + 1}</span>
                  </div>
                  <div className={`mt-3 text-sm font-bold ${active ? 'text-white' : 'text-slate-900'}`}>{step.title}</div>
                  <div className={`text-[11px] mt-0.5 ${active ? 'text-emerald-300' : 'text-emerald-700 font-semibold'}`}>{step.who}</div>
                  <p className={`text-[11px] mt-2 leading-relaxed ${active ? 'text-blue-200' : 'text-slate-500'}`}>{step.summary}</p>
                </button>
              </Reveal>
            );
          })}
        </div>

        <Reveal>
          <div className="max-w-3xl mx-auto rounded-xl border border-slate-200 bg-slate-50/70 p-6">
            {open === -1 ? (
              <p className="text-sm text-slate-600 italic">Select a stage above to read what happens there.</p>
            ) : (
              <div className="flex items-start gap-4">
                <div className="w-12 h-12 rounded-xl bg-blue-900 text-amber-400 flex items-center justify-center shrink-0 shadow-sm">
                  {(() => {
                    const Icon = STEPS[open].icon;
                    return <Icon className="w-6 h-6" />;
                  })()}
                </div>
                <div>
                  <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wide">
                    Stage 0{open + 1} · for the {STEPS[open].who}
                  </div>
                  <h3 className="text-base font-bold text-slate-900 mt-0.5">{STEPS[open].title}</h3>
                  <p className="text-sm text-slate-600 mt-2 leading-relaxed">{STEPS[open].detail}</p>
                </div>
              </div>
            )}
          </div>
        </Reveal>
      </div>
    </section>
  );
};

/* --------------------------- FAQs --------------------------- */

const FAQS = [
  {
    q: 'Do I need to be a Scheduled Tribe student to apply?',
    a: 'Yes. Every scheme targets ST students, and the ST certificate is the key document an officer verifies against what you declared. That verification is human — the platform never authenticates a document by itself.',
  },
  {
    q: 'Where are my documents kept? Are they safe?',
    a: 'Uploads go into MongoDB GridFS, inside the same database as the platform — not to a folder on a server. Files are limited to 10 MB, checked by extension and byte signature, and stream only through a private route that the applicant and an officer can call.',
  },
  {
    q: 'Does the system decide my application automatically?',
    a: 'No. It checks declared values against configured rules, compares them with extracted document text, and can order a queue by marks — all as aids. Selection and approval are recorded human decisions, each with written reasons in the audit trail.',
  },
  {
    q: 'What if I miss a document?',
    a: 'You are marked deficient — not rejected. The missing document is named, you correct and re-submit, and while the application is still open you may also withdraw it entirely.',
  },
  {
    q: 'Which of my details does the platform rely on?',
    a: 'What you declare is recorded side by side with what your documents say. Where they disagree, the officer sees both and the reason for the discrepancy is computed from configured rules, not guessed at.',
  },
  {
    q: 'Is AROHAN-ST a live government service?',
    a: 'It is a working prototype. Identity federation with official sources, official quotas and rosters, and payment/DBT integration are deliberately out of scope — the platform makes a human decision visible and repeatable, it does not claim to be one.',
  },
];

const FaqSection: React.FC = () => {
  const [openIndex, setOpenIndex] = useState<number>(0);
  return (
    <section id="faq" className="max-w-3xl mx-auto px-4 sm:px-6 py-16 sm:py-20">
      <Reveal className="text-center mb-10">
        <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-blue-100 text-blue-900 border border-blue-200 uppercase tracking-wide">
          Honest Questions
        </span>
        <h2 className="text-2xl sm:text-3xl font-bold text-slate-950 mt-2">Frequently asked</h2>
      </Reveal>
      <div className="space-y-3">
        {FAQS.map((faq, i) => {
          const open = openIndex === i;
          return (
            <Reveal key={faq.q} delay={i * 50}>
              <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
                <button
                  onClick={() => setOpenIndex(open ? -1 : i)}
                  className="w-full flex items-center justify-between gap-4 p-4 text-left"
                >
                  <span className="text-sm font-semibold text-slate-900 flex items-center gap-3">
                    <HelpCircle className="w-4 h-4 text-blue-700 flex-shrink-0" />
                    {faq.q}
                  </span>
                  <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform ${open ? 'rotate-180' : ''}`} />
                </button>
                <div
                  className={`grid transition-all duration-300 ease-in-out ${
                    open ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]'
                  }`}
                >
                  <div className="overflow-hidden">
                    <p className="px-4 pb-4 pl-11 text-sm text-slate-600 leading-relaxed">{faq.a}</p>
                  </div>
                </div>
              </div>
            </Reveal>
          );
        })}
      </div>
    </section>
  );
};

/* --------------------------- CTAs --------------------------- */

const CtaBand: React.FC<{ onGetStarted: () => void; onSignIn: () => void }> = ({ onGetStarted, onSignIn }) => (
  <section className="bg-blue-950 border-t border-blue-900 py-16">
    <div className="max-w-4xl mx-auto px-4 sm:px-6 text-center">
      <Reveal>
        <div className="w-16 h-16 rounded-2xl bg-blue-800 text-amber-400 flex items-center justify-center mx-auto mb-6 shadow-lg">
          <Landmark className="w-8 h-8" />
        </div>
        <h2 className="text-2xl sm:text-3xl font-bold text-white">
          Your climb starts here.
        </h2>
        <p className="text-sm text-blue-200 mt-3 max-w-2xl mx-auto leading-relaxed">
          Register in under a minute, apply to any of the five schemes, and watch every stage — from first upload to
          final sanction — in one place.
        </p>
        <div className="flex flex-col sm:flex-row items-center justify-center gap-3 mt-8">
          <button
            onClick={onGetStarted}
            className="flex items-center gap-2 px-6 py-3 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-sm shadow-lg transition"
          >
            <UserCheck className="w-4 h-4" />
            Start Your Application
          </button>
          <button
            onClick={onSignIn}
            className="flex items-center gap-2 px-6 py-3 rounded-lg bg-white/10 hover:bg-white/20 border border-blue-800 text-white font-semibold text-sm transition"
          >
            I am an officer with an account
          </button>
        </div>
        <p className="text-[11px] text-blue-300/80 mt-6">
          Prototype platform for the Ministry of Tribal Affairs. Documents are verified by officers, and decisions are
          always recorded human decisions.
        </p>
      </Reveal>
    </div>
  </section>
);

/* --------------------------- landing --------------------------- */

export const Landing: React.FC<LandingProps> = ({ onGetStarted, onSignIn }) => {
  const scrollTo = (id: string) => {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <div className="bg-slate-50 text-slate-800">
      {/* Hero */}
      <section className="bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-14 sm:pt-20 pb-12 sm:pb-16 text-center">
          <Reveal>
            <div className="inline-flex items-center gap-2 text-xs font-semibold px-3 py-1.5 rounded-full bg-blue-50 text-blue-900 border border-blue-200 mb-6">
              <Sparkles className="w-3.5 h-3.5 text-amber-500" />
              Ministry of Tribal Affairs · Scholarship &amp; Fellowship Management
            </div>
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black tracking-tight text-blue-950">
              AROHAN-ST
              <span className="block text-lg sm:text-xl font-bold text-slate-500 mt-3">
                आरोहण — the climb from application to sanction
              </span>
            </h1>
            <p className="mt-6 min-h-[1.75rem] text-base sm:text-lg text-slate-600 max-w-3xl mx-auto">
              <Typewriter />
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-3 mt-8">
              <button
                onClick={onGetStarted}
                className="flex items-center gap-2 px-6 py-3 rounded-lg bg-blue-900 hover:bg-blue-800 text-white font-semibold text-sm shadow-md transition"
              >
                <UserCheck className="w-4 h-4" />
                Start Your Application
                <ArrowRight className="w-4 h-4" />
              </button>
              <button
                onClick={() => scrollTo('schemes')}
                className="flex items-center gap-2 px-6 py-3 rounded-lg bg-white border border-slate-300 hover:border-blue-300 text-slate-700 hover:text-blue-900 font-semibold text-sm transition"
              >
                <GraduationCap className="w-4 h-4" />
                Explore the Schemes
              </button>
            </div>
          </Reveal>

          {/* Stats */}
          <Reveal delay={150}>
            <div className="mt-12 grid grid-cols-2 md:grid-cols-4 gap-4 max-w-4xl mx-auto">
              {[
                { to: 5, suffix: '', label: 'National ST schemes' },
                { to: 20, suffix: '+', label: 'Verifiable document types' },
                { to: 100, suffix: '%', label: 'Evidence kept in MongoDB GridFS' },
                { to: 2, suffix: '', label: 'Roles — scholar & officer' },
              ].map((s) => (
                <div key={s.label} className="bg-slate-50 border border-slate-200 rounded-xl p-4">
                  <div className="text-3xl font-black text-blue-900">
                    <CountUp to={s.to} suffix={s.suffix} />
                  </div>
                  <div className="text-[11px] text-slate-500 mt-1 font-medium">{s.label}</div>
                </div>
              ))}
            </div>
          </Reveal>
        </div>
      </section>

      <ValueMarquee />
      <ValuesSection />
      <GoalsSection />
      <SchemesExplorer />
      <PathwaySection />
      <FaqSection />
      <CtaBand onGetStarted={onGetStarted} onSignIn={onSignIn} />
    </div>
  );
};