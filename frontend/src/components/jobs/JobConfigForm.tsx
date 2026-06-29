'use client';

import React, { useState } from 'react';
import { Card, Button, Input, Textarea, Switch } from '@/components/ui';
import { Select, SelectTrigger, SelectContent, SelectItem, SelectValue } from '@/components/ui/select';

type Provider = 'serpapi' | 'apify' | 'custom' | 'browserless' | 'twitter' | 'reddit';

interface JobConfig {
  // Common
  urls?: string[];
  query?: string;
  
  // Scraping options
  selector?: string;
  wait_for?: string;
  extract_type?: 'text' | 'html' | 'links' | 'images' | 'screenshot';
  
  // Media options
  download_media?: boolean;
  
  // Proxy options
  use_proxy?: boolean;
  proxy_strategy?: 'round_robin' | 'random' | 'best_performance';
  proxies?: Array<{
    url: string;
    protocol?: string;
    username?: string;
    password?: string;
  }>;
  
  // Browserless specific
  take_screenshot?: boolean;
  extract_pdf?: boolean;
  full_page?: boolean;
  viewport?: {
    width: number;
    height: number;
  };
  
  // SerpAPI specific
  search_type?: 'web' | 'images' | 'news' | 'videos';
  num_results?: number;
  
  // Twitter specific
  max_tweets?: number;
  
  // Reddit specific
  subreddit?: string;
  sort?: string;
  limit?: number;
}

interface JobConfigFormProps {
  provider: Provider;
  initialConfig?: JobConfig;
  onSubmit: (config: JobConfig) => void;
  onCancel?: () => void;
  isLoading?: boolean;
}

const providerInfo = {
  serpapi: {
    name: 'SerpAPI',
    description: 'جستجو در گوگل و موتورهای جستجوی دیگر',
    fields: ['query', 'search_type', 'num_results'],
  },
  apify: {
    name: 'Apify',
    description: 'اجرای اکتورهای Apify برای اسکرپینگ',
    fields: ['urls', 'selector', 'wait_for'],
  },
  custom: {
    name: 'سفارشی',
    description: 'اسکرپینگ ساده از URL ها',
    fields: ['urls', 'selector', 'extract_type', 'download_media'],
  },
  browserless: {
    name: 'Browserless',
    description: 'اسکرپینگ با Chrome بدون سر برای صفحات JavaScript',
    fields: ['urls', 'selector', 'wait_for', 'extract_type', 'take_screenshot', 'extract_pdf'],
  },
  twitter: {
    name: 'Twitter',
    description: 'جمع‌آوری توییت‌ها',
    fields: ['query', 'max_tweets'],
  },
  reddit: {
    name: 'Reddit',
    description: 'جمع‌آوری پست‌های Reddit',
    fields: ['subreddit', 'sort', 'limit'],
  },
};

export function JobConfigForm({
  provider,
  initialConfig = {},
  onSubmit,
  onCancel,
  isLoading = false,
}: JobConfigFormProps) {
  const [config, setConfig] = useState<JobConfig>(initialConfig);
  const [urlInput, setUrlInput] = useState(initialConfig.urls?.join('\n') || '');
  const [showProxySettings, setShowProxySettings] = useState(initialConfig.use_proxy || false);
  const [proxyInput, setProxyInput] = useState('');

  const info = providerInfo[provider];
  const fields = info.fields;

  const updateConfig = (key: keyof JobConfig, value: any) => {
    setConfig(prev => ({ ...prev, [key]: value }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    const finalConfig = { ...config };
    
    // Process URLs
    if (urlInput) {
      finalConfig.urls = urlInput
        .split('\n')
        .map(url => url.trim())
        .filter(url => url.length > 0);
    }
    
    // Process proxies
    if (proxyInput && showProxySettings) {
      finalConfig.proxies = proxyInput
        .split('\n')
        .map(line => line.trim())
        .filter(line => line.length > 0)
        .map(url => ({ url, protocol: url.startsWith('socks') ? 'socks5' : 'http' }));
      finalConfig.use_proxy = true;
    }
    
    onSubmit(finalConfig);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Provider Info */}
      <Card className="p-4 bg-blue-50 border-blue-200">
        <h3 className="font-semibold text-blue-800">{info.name}</h3>
        <p className="text-sm text-blue-600 mt-1">{info.description}</p>
      </Card>

      {/* Common Fields */}
      {fields.includes('urls') && (
        <div>
          <label className="block text-sm font-medium mb-2">
            آدرس‌های URL (هر خط یک URL)
          </label>
          <Textarea
            value={urlInput}
            onChange={(e) => setUrlInput(e.target.value)}
            placeholder="https://example.com/page1&#10;https://example.com/page2"
            rows={5}
          />
        </div>
      )}

      {fields.includes('query') && (
        <div>
          <label className="block text-sm font-medium mb-2">
            عبارت جستجو
          </label>
          <Input
            value={config.query || ''}
            onChange={(e) => updateConfig('query', e.target.value)}
            placeholder="عبارت مورد نظر برای جستجو"
          />
        </div>
      )}

      {fields.includes('selector') && (
        <div>
          <label className="block text-sm font-medium mb-2">
            سلکتور CSS (اختیاری)
          </label>
          <Input
            value={config.selector || ''}
            onChange={(e) => updateConfig('selector', e.target.value)}
            placeholder="article.content, .main-text, #post-body"
          />
          <p className="text-xs text-gray-500 mt-1">
            اگر خالی باشد، کل محتوای صفحه استخراج می‌شود
          </p>
        </div>
      )}

      {fields.includes('wait_for') && (
        <div>
          <label className="block text-sm font-medium mb-2">
            منتظر سلکتور (برای صفحات JavaScript)
          </label>
          <Input
            value={config.wait_for || ''}
            onChange={(e) => updateConfig('wait_for', e.target.value)}
            placeholder=".loaded, #content-ready"
          />
        </div>
      )}

      {fields.includes('extract_type') && (
        <div>
          <label className="block text-sm font-medium mb-2">
            نوع استخراج
          </label>
          <Select
            value={config.extract_type || 'text'}
            onValueChange={(value) => updateConfig('extract_type', value as any)}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="text">متن</SelectItem>
              <SelectItem value="html">HTML</SelectItem>
              <SelectItem value="links">لینک‌ها</SelectItem>
              <SelectItem value="images">تصاویر</SelectItem>
              {provider === 'browserless' && (
                <SelectItem value="screenshot">اسکرین‌شات</SelectItem>
              )}
            </SelectContent>
          </Select>
        </div>
      )}

      {/* SerpAPI specific */}
      {fields.includes('search_type') && (
        <div>
          <label className="block text-sm font-medium mb-2">
            نوع جستجو
          </label>
          <Select
            value={config.search_type || 'web'}
            onValueChange={(value) => updateConfig('search_type', value as any)}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="web">وب</SelectItem>
              <SelectItem value="images">تصاویر</SelectItem>
              <SelectItem value="news">اخبار</SelectItem>
              <SelectItem value="videos">ویدیوها</SelectItem>
            </SelectContent>
          </Select>
        </div>
      )}

      {fields.includes('num_results') && (
        <div>
          <label className="block text-sm font-medium mb-2">
            تعداد نتایج
          </label>
          <Input
            type="number"
            value={config.num_results || 10}
            onChange={(e) => updateConfig('num_results', parseInt(e.target.value))}
            min={1}
            max={100}
          />
        </div>
      )}

      {/* Twitter specific */}
      {fields.includes('max_tweets') && (
        <div>
          <label className="block text-sm font-medium mb-2">
            حداکثر توییت
          </label>
          <Input
            type="number"
            value={config.max_tweets || 100}
            onChange={(e) => updateConfig('max_tweets', parseInt(e.target.value))}
            min={1}
            max={1000}
          />
        </div>
      )}

      {/* Reddit specific */}
      {fields.includes('subreddit') && (
        <div>
          <label className="block text-sm font-medium mb-2">
            ساب‌ردیت
          </label>
          <Input
            value={config.subreddit || ''}
            onChange={(e) => updateConfig('subreddit', e.target.value)}
            placeholder="MachineLearning"
          />
        </div>
      )}

      {fields.includes('sort') && (
        <div>
          <label className="block text-sm font-medium mb-2">
            ترتیب
          </label>
          <Select
            value={config.sort || 'hot'}
            onValueChange={(value) => updateConfig('sort', value)}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="hot">داغ</SelectItem>
              <SelectItem value="new">جدید</SelectItem>
              <SelectItem value="top">برتر</SelectItem>
              <SelectItem value="rising">در حال صعود</SelectItem>
            </SelectContent>
          </Select>
        </div>
      )}

      {fields.includes('limit') && (
        <div>
          <label className="block text-sm font-medium mb-2">
            تعداد پست
          </label>
          <Input
            type="number"
            value={config.limit || 25}
            onChange={(e) => updateConfig('limit', parseInt(e.target.value))}
            min={1}
            max={100}
          />
        </div>
      )}

      {/* Browserless specific */}
      {fields.includes('take_screenshot') && (
        <div className="flex items-center gap-3">
          <Switch
            checked={config.take_screenshot || false}
            onCheckedChange={(checked) => updateConfig('take_screenshot', checked)}
          />
          <label className="text-sm font-medium">گرفتن اسکرین‌شات</label>
        </div>
      )}

      {fields.includes('extract_pdf') && (
        <div className="flex items-center gap-3">
          <Switch
            checked={config.extract_pdf || false}
            onCheckedChange={(checked) => updateConfig('extract_pdf', checked)}
          />
          <label className="text-sm font-medium">تولید PDF</label>
        </div>
      )}

      {/* Media Download */}
      {fields.includes('download_media') && (
        <div className="flex items-center gap-3">
          <Switch
            checked={config.download_media || false}
            onCheckedChange={(checked) => updateConfig('download_media', checked)}
          />
          <label className="text-sm font-medium">دانلود فایل‌های مدیا</label>
        </div>
      )}

      {/* Proxy Settings */}
      <Card className="p-4">
        <div className="flex items-center justify-between mb-4">
          <h4 className="font-medium">تنظیمات پروکسی</h4>
          <Switch
            checked={showProxySettings}
            onCheckedChange={setShowProxySettings}
          />
        </div>

        {showProxySettings && (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">
                استراتژی انتخاب پروکسی
              </label>
              <Select
                value={config.proxy_strategy || 'round_robin'}
                onValueChange={(value) => updateConfig('proxy_strategy', value as any)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="round_robin">چرخشی</SelectItem>
                  <SelectItem value="random">تصادفی</SelectItem>
                  <SelectItem value="best_performance">بهترین عملکرد</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">
                لیست پروکسی (هر خط یک پروکسی)
              </label>
              <Textarea
                value={proxyInput}
                onChange={(e) => setProxyInput(e.target.value)}
                placeholder="http://proxy1.example.com:8080&#10;socks5://proxy2.example.com:1080"
                rows={4}
              />
              <p className="text-xs text-gray-500 mt-1">
                فرمت: http://host:port یا socks5://user:pass@host:port
              </p>
            </div>
          </div>
        )}
      </Card>

      {/* Actions */}
      <div className="flex gap-3 justify-end">
        {onCancel && (
          <Button
            type="button"
            variant="outline"
            onClick={onCancel}
            disabled={isLoading}
          >
            انصراف
          </Button>
        )}
        <Button type="submit" disabled={isLoading}>
          {isLoading ? 'در حال ذخیره...' : 'ذخیره تنظیمات'}
        </Button>
      </div>
    </form>
  );
}

