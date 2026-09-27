import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertOctagon, RotateCcw } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallbackTitle?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught error:', error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="bg-[#0b101b] rounded-xl border border-rose-900/60 p-6 flex flex-col items-center justify-center text-center gap-3">
          <AlertOctagon className="w-10 h-10 text-rose-500 animate-pulse" />
          <h4 className="font-mono text-sm font-bold text-white">
            {this.props.fallbackTitle || 'Component Telemetry Offline'}
          </h4>
          <p className="font-mono text-xs text-slate-400 max-w-md">
            {this.state.error?.message || 'Unexpected rendering error occurred. Rest of the cockpit remains active.'}
          </p>
          <button
            onClick={() => this.setState({ hasError: false, error: null })}
            className="mt-2 flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-slate-800 hover:bg-slate-700 text-cyan-400 text-xs font-mono font-semibold"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Retry Component</span>
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
