-- Add plan column to user_profiles for gating CRX/ZIP upload (free vs pro)
alter table "public"."user_profiles"
  add column if not exists "plan" text not null default 'free';

comment on column "public"."user_profiles"."plan" is 'User plan: free or pro. Pro required for CRX/ZIP upload.';
