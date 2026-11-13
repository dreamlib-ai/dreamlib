export type IconName = 'person' | 'heart' | 'send' | 'stop' | 'upload' | 'loader' | 'home' | 'pen' | 'book' | 'moon' | 'compass' | 'check' | 'chevron' | 'logout' | 'cloud' | 'waves' | 'door' | 'mic' | 'search' | 'plus';
const paths: Record<IconName, string> = {
  person: 'M20 21v-2a7 7 0 0 0-14 0v2M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0Z',
  heart: 'M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8L12 21l8.8-8.6a5.5 5.5 0 0 0 0-7.8Z',
  send: 'M12 19V5m-6 6 6-6 6 6',
  stop: 'M7 7h10v10H7Z',
  upload: 'M12 16V3m-5 5 5-5 5 5M4 16v5h16v-5',
  loader: 'M21 12a9 9 0 1 1-9-9',
  cloud: 'M7 18a5 5 0 1 1 1-9 6 6 0 0 1 11 3 3 3 0 0 1-1 6Z',
  waves: 'M2 8c3-4 5 4 9 0s6 4 11 0M2 13c3-4 5 4 9 0s6 4 11 0M2 18c3-4 5 4 9 0s6 4 11 0',
  door: 'M4 21h16M7 21V3h10v18M13 12h.01',
  mic: 'M9 5a3 3 0 0 1 6 0v7a3 3 0 0 1-6 0ZM5 10v2a7 7 0 0 0 14 0v-2M12 19v3m-4 0h8',
  search: 'M21 21l-5-5M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0Z',
  plus: 'M12 5v14M5 12h14',
  logout: 'M9 4H4v16h5m6-12 4 4-4 4m-7-4h11',
  home: 'm3 10 9-7 9 7v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1Z',
  pen: 'm15 4 5 5M4 20l5-1L21 7a2 2 0 0 0-4-4L5 15Z',
  book: 'M12 6v15M3 4c4-1 6 0 9 2 3-2 5-3 9-2v15c-4-1-6 0-9 2-3-2-5-3-9-2Z',
  moon: 'M20 14A8 8 0 0 1 10 4a8 8 0 1 0 10 10Z',
  compass: 'M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-5-4-3 5-5 3 3-5Z',
  check: 'm5 12 4 4L19 6',
  chevron: 'm14 5-7 7 7 7',
};
export default function Icon({ name, className = '' }: { name: IconName; className?: string }) {
  return <svg className={`icon ${className}`} width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name]} /></svg>;
}
