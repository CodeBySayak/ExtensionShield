-- Private upload reports: user_id, visibility, source for scan_results
-- Uploads: visibility='private', source='upload'. Public feed filters to visibility='public' and source='webstore'.

alter table public.scan_results
  add column if not exists user_id uuid references auth.users(id) on delete set null;

alter table public.scan_results
  add column if not exists visibility text not null default 'public';

alter table public.scan_results
  add column if not exists source text not null default 'webstore';

comment on column public.scan_results.user_id is 'Owner for private uploads; NULL for public webstore scans.';
comment on column public.scan_results.visibility is 'public | private. Private = only user_id can view.';
comment on column public.scan_results.source is 'webstore | upload. Upload scans excluded from public recent feed.';

create index if not exists idx_scan_results_visibility_source
  on public.scan_results(visibility, source)
  where visibility = 'public' and source = 'webstore';
