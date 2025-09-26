export interface LoginFeatureItem {
  icon: string;
  iconLabel: string;
  heading: string;
  description: string;
}

export interface LoginFeaturesConfig {
  title: string;
  subtitle?: string;
  features: LoginFeatureItem[];
}

export const defaultLoginFeaturesConfig: LoginFeaturesConfig = {
  title: 'Why Choose JEEX Plan?',
  subtitle: undefined,
  features: [
    {
      icon: '🤖',
      iconLabel: 'Robot icon',
      heading: 'AI-Powered Documentation',
      description:
        'Generate comprehensive technical documentation using advanced AI agents',
    },
    {
      icon: '⚡',
      iconLabel: 'High voltage icon',
      heading: 'Multi-Agent System',
      description:
        'Specialized agents for different aspects of documentation generation',
    },
    {
      icon: '🔒',
      iconLabel: 'Padlock icon',
      heading: 'Secure & Multi-Tenant',
      description: 'Enterprise-grade security with complete tenant isolation',
    },
    {
      icon: '📊',
      iconLabel: 'Bar chart icon',
      heading: 'Real-Time Progress',
      description: 'Track documentation generation progress in real-time',
    },
  ],
};
