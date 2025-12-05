-- Enable Row Level Security (RLS) for all TradeAgent tables
-- This prevents unauthorized access via PostgREST API

-- Enable RLS on all tables
ALTER TABLE public.daily_performance ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.trades ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.strategy_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.parameter_changes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.weekly_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ml_training_data ENABLE ROW LEVEL SECURITY;

-- Create policies that allow access only with service_role key
-- This ensures only your backend/bot can access the data

-- Policy for daily_performance
CREATE POLICY "Service role can do everything on daily_performance"
ON public.daily_performance
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- Policy for trades
CREATE POLICY "Service role can do everything on trades"
ON public.trades
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- Policy for signals
CREATE POLICY "Service role can do everything on signals"
ON public.signals
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- Policy for strategy_metrics
CREATE POLICY "Service role can do everything on strategy_metrics"
ON public.strategy_metrics
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- Policy for parameter_changes
CREATE POLICY "Service role can do everything on parameter_changes"
ON public.parameter_changes
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- Policy for weekly_reports
CREATE POLICY "Service role can do everything on weekly_reports"
ON public.weekly_reports
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- Policy for ml_training_data
CREATE POLICY "Service role can do everything on ml_training_data"
ON public.ml_training_data
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- Verify RLS is enabled
SELECT
    schemaname,
    tablename,
    rowsecurity AS rls_enabled
FROM pg_tables
WHERE schemaname = 'public'
    AND tablename IN (
        'daily_performance',
        'trades',
        'signals',
        'strategy_metrics',
        'parameter_changes',
        'weekly_reports',
        'ml_training_data'
    )
ORDER BY tablename;
