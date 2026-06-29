'use client';

import { useLocale, useTranslations } from 'next-intl';
import { usePathname, useRouter } from '@/i18n/navigation';
import { locales, localeNames, localeFlags, type Locale } from '@/i18n/config';
import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Globe, ChevronDown, Check } from 'lucide-react';

export function LanguageSwitcher() {
  const locale = useLocale() as Locale;
  const router = useRouter();
  const pathname = usePathname();
  const t = useTranslations('languages');
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleLocaleChange = (newLocale: Locale) => {
    router.replace(pathname, { locale: newLocale });
    setIsOpen(false);
  };

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-2 rounded-xl bg-surface-800/50 hover:bg-surface-800 transition-colors border border-surface-700/50"
      >
        <Globe className="w-4 h-4 text-surface-400" />
        <span className="text-sm font-medium">{localeFlags[locale]} {localeNames[locale]}</span>
        <ChevronDown className={`w-4 h-4 text-surface-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: -10, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.95 }}
            transition={{ duration: 0.15 }}
            className="absolute top-full mt-2 end-0 min-w-[160px] rounded-xl bg-surface-900 border border-surface-800 shadow-xl z-50 overflow-hidden"
          >
            {locales.map((loc) => (
              <button
                key={loc}
                onClick={() => handleLocaleChange(loc)}
                className={`flex items-center gap-3 w-full px-4 py-3 text-sm hover:bg-surface-800 transition-colors ${
                  locale === loc ? 'bg-brand-500/10 text-brand-400' : 'text-surface-300'
                }`}
              >
                <span className="text-lg">{localeFlags[loc]}</span>
                <span className="flex-1 text-start">{localeNames[loc]}</span>
                {locale === loc && <Check className="w-4 h-4 text-brand-400" />}
              </button>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// Compact version for sidebar
export function LanguageSwitcherCompact() {
  const locale = useLocale() as Locale;
  const router = useRouter();
  const pathname = usePathname();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleLocaleChange = (newLocale: Locale) => {
    router.replace(pathname, { locale: newLocale });
    setIsOpen(false);
  };

  const currentIndex = locales.indexOf(locale);
  const nextLocale = locales[(currentIndex + 1) % locales.length];

  return (
    <button
      onClick={() => handleLocaleChange(nextLocale)}
      className="flex items-center gap-2 px-3 py-2 rounded-xl hover:bg-surface-800 transition-colors text-surface-400 hover:text-white"
      title={`Switch to ${localeNames[nextLocale]}`}
    >
      <Globe className="w-5 h-5" />
      <span className="text-lg">{localeFlags[locale]}</span>
    </button>
  );
}

