-- Seed local dev users, tenant, and memberships.
-- Password for all users: Passw0rd!

-- Ensure a default auth instance exists (required for GoTrue login)
INSERT INTO auth.instances (id, uuid, created_at, updated_at)
VALUES (
  '00000000-0000-0000-0000-000000000000',
  '00000000-0000-0000-0000-000000000000',
  now(),
  now()
)
ON CONFLICT (id) DO NOTHING;

-- Clean up existing seed users (idempotent for local reset)
DELETE FROM auth.identities
WHERE provider = 'email'
  AND email IN (
    'root@actbi.ai',
    'superadmin@actbi.ai',
    'admin@actbi.ai',
    'creator@actbi.ai',
    'viewer@actbi.ai'
  );

DELETE FROM auth.users
WHERE email IN (
    'root@actbi.ai',
    'superadmin@actbi.ai',
    'admin@actbi.ai',
    'creator@actbi.ai',
    'viewer@actbi.ai'
  );

-- Users
INSERT INTO auth.users (
  id,
  instance_id,
  aud,
  role,
  email,
  encrypted_password,
  email_confirmed_at,
  confirmation_token,
  recovery_token,
  email_change_token_new,
  email_change_token_current,
  email_change,
  reauthentication_token,
  raw_app_meta_data,
  raw_user_meta_data,
  created_at,
  updated_at
)
VALUES
  (
    '64c467b9-a2ed-417f-b1a7-4fc00764e9b4',
    '00000000-0000-0000-0000-000000000000',
    'authenticated',
    'authenticated',
    'root@actbi.ai',
    crypt('Passw0rd!', gen_salt('bf')),
    now(),
    '',
    '',
    '',
    '',
    '',
    '',
    '{"provider":"email","providers":["email"]}',
    '{"email_verified":true}',
    now(),
    now()
  ),
  (
    '313df076-8796-4bb2-a589-ae2c271a7e04',
    '00000000-0000-0000-0000-000000000000',
    'authenticated',
    'authenticated',
    'superadmin@actbi.ai',
    crypt('Passw0rd!', gen_salt('bf')),
    now(),
    '',
    '',
    '',
    '',
    '',
    '',
    '{"provider":"email","providers":["email"]}',
    '{"email_verified":true}',
    now(),
    now()
  ),
  (
    '0df63f12-1966-4a50-bb39-db83dda9b143',
    '00000000-0000-0000-0000-000000000000',
    'authenticated',
    'authenticated',
    'admin@actbi.ai',
    crypt('Passw0rd!', gen_salt('bf')),
    now(),
    '',
    '',
    '',
    '',
    '',
    '',
    '{"provider":"email","providers":["email"]}',
    '{"email_verified":true}',
    now(),
    now()
  ),
  (
    'ab3f0554-25a2-4354-81ae-7781a97f32af',
    '00000000-0000-0000-0000-000000000000',
    'authenticated',
    'authenticated',
    'creator@actbi.ai',
    crypt('Passw0rd!', gen_salt('bf')),
    now(),
    '',
    '',
    '',
    '',
    '',
    '',
    '{"provider":"email","providers":["email"]}',
    '{"email_verified":true}',
    now(),
    now()
  ),
  (
    '5cf1e66d-4261-4bad-92bb-4e30f1cde8c3',
    '00000000-0000-0000-0000-000000000000',
    'authenticated',
    'authenticated',
    'viewer@actbi.ai',
    crypt('Passw0rd!', gen_salt('bf')),
    now(),
    '',
    '',
    '',
    '',
    '',
    '',
    '{"provider":"email","providers":["email"]}',
    '{"email_verified":true}',
    now(),
    now()
  );

-- Identities for email provider
INSERT INTO auth.identities (
  provider_id,
  user_id,
  identity_data,
  provider,
  last_sign_in_at,
  created_at,
  updated_at
)
VALUES
  (
    '64c467b9-a2ed-417f-b1a7-4fc00764e9b4',
    '64c467b9-a2ed-417f-b1a7-4fc00764e9b4',
    '{"sub":"64c467b9-a2ed-417f-b1a7-4fc00764e9b4","email":"root@actbi.ai","email_verified":true}',
    'email',
    now(),
    now(),
    now()
  ),
  (
    '313df076-8796-4bb2-a589-ae2c271a7e04',
    '313df076-8796-4bb2-a589-ae2c271a7e04',
    '{"sub":"313df076-8796-4bb2-a589-ae2c271a7e04","email":"superadmin@actbi.ai","email_verified":true}',
    'email',
    now(),
    now(),
    now()
  ),
  (
    '0df63f12-1966-4a50-bb39-db83dda9b143',
    '0df63f12-1966-4a50-bb39-db83dda9b143',
    '{"sub":"0df63f12-1966-4a50-bb39-db83dda9b143","email":"admin@actbi.ai","email_verified":true}',
    'email',
    now(),
    now(),
    now()
  ),
  (
    'ab3f0554-25a2-4354-81ae-7781a97f32af',
    'ab3f0554-25a2-4354-81ae-7781a97f32af',
    '{"sub":"ab3f0554-25a2-4354-81ae-7781a97f32af","email":"creator@actbi.ai","email_verified":true}',
    'email',
    now(),
    now(),
    now()
  ),
  (
    '5cf1e66d-4261-4bad-92bb-4e30f1cde8c3',
    '5cf1e66d-4261-4bad-92bb-4e30f1cde8c3',
    '{"sub":"5cf1e66d-4261-4bad-92bb-4e30f1cde8c3","email":"viewer@actbi.ai","email_verified":true}',
    'email',
    now(),
    now(),
    now()
  );

-- Tenants (2 tenants for RLS exercise: issue #2 / Project 1)
INSERT INTO public.tenants (id, name, description, status)
VALUES
  (
    '1c047e98-dd0c-46e9-bc99-1a0314282c64',
    'Acme',
    'Seed tenant',
    'active'
  ),
  (
    'a2b3c4d5-e6f7-4901-2345-67890abcdef1',
    'Beta Corp',
    'Second seed tenant for RLS testing',
    'active'
  )
ON CONFLICT (id) DO UPDATE SET
  name = EXCLUDED.name,
  description = EXCLUDED.description,
  status = EXCLUDED.status;

-- Profiles (root is global admin)
INSERT INTO public.user_profiles (id, email, display_name, is_app_admin)
VALUES
  ('64c467b9-a2ed-417f-b1a7-4fc00764e9b4', 'root@actbi.ai', 'Root Admin', true),
  ('313df076-8796-4bb2-a589-ae2c271a7e04', 'superadmin@actbi.ai', 'Super Admin', false),
  ('0df63f12-1966-4a50-bb39-db83dda9b143', 'admin@actbi.ai', 'Admin User', false),
  ('ab3f0554-25a2-4354-81ae-7781a97f32af', 'creator@actbi.ai', 'Creator User', false),
  ('5cf1e66d-4261-4bad-92bb-4e30f1cde8c3', 'viewer@actbi.ai', 'Viewer User', false)
ON CONFLICT (id) DO UPDATE SET
  email = EXCLUDED.email,
  display_name = EXCLUDED.display_name,
  is_app_admin = EXCLUDED.is_app_admin;

-- Tenant membership roles (Acme: 5 users; Beta: 1 user as creator for RLS exercise)
INSERT INTO public.tenant_users (tenant_id, user_id, role, status, accepted_at)
VALUES
  ('1c047e98-dd0c-46e9-bc99-1a0314282c64', '64c467b9-a2ed-417f-b1a7-4fc00764e9b4', 'superadmin', 'active', now()),
  ('1c047e98-dd0c-46e9-bc99-1a0314282c64', '313df076-8796-4bb2-a589-ae2c271a7e04', 'superadmin', 'active', now()),
  ('1c047e98-dd0c-46e9-bc99-1a0314282c64', '0df63f12-1966-4a50-bb39-db83dda9b143', 'admin', 'active', now()),
  ('1c047e98-dd0c-46e9-bc99-1a0314282c64', 'ab3f0554-25a2-4354-81ae-7781a97f32af', 'creator', 'active', now()),
  ('1c047e98-dd0c-46e9-bc99-1a0314282c64', '5cf1e66d-4261-4bad-92bb-4e30f1cde8c3', 'viewer', 'active', now()),
  ('a2b3c4d5-e6f7-4901-2345-67890abcdef1', '5cf1e66d-4261-4bad-92bb-4e30f1cde8c3', 'creator', 'active', now())
ON CONFLICT (tenant_id, user_id) DO UPDATE SET
  role = EXCLUDED.role,
  status = EXCLUDED.status,
  accepted_at = EXCLUDED.accepted_at;

-- Dashboards: one per tenant to exercise RLS (tenant isolation)
INSERT INTO public.dashboards (id, tenant_id, owner_user_id, title, description)
VALUES
  ('d1111111-1111-1111-1111-111111111111', '1c047e98-dd0c-46e9-bc99-1a0314282c64', 'ab3f0554-25a2-4354-81ae-7781a97f32af', 'Acme Dashboard', 'Seed dashboard for Tenant Acme'),
  ('d2222222-2222-2222-2222-222222222222', 'a2b3c4d5-e6f7-4901-2345-67890abcdef1', '5cf1e66d-4261-4bad-92bb-4e30f1cde8c3', 'Beta Dashboard', 'Seed dashboard for Tenant Beta')
ON CONFLICT (id) DO UPDATE SET
  tenant_id = EXCLUDED.tenant_id,
  owner_user_id = EXCLUDED.owner_user_id,
  title = EXCLUDED.title,
  description = EXCLUDED.description;

-- Conversations: one per tenant to exercise RLS (tenant isolation)
INSERT INTO public.conversations (id, tenant_id, owner_user_id, title)
VALUES
  ('c1111111-1111-1111-1111-111111111111', '1c047e98-dd0c-46e9-bc99-1a0314282c64', 'ab3f0554-25a2-4354-81ae-7781a97f32af', 'Acme Chat'),
  ('c2222222-2222-2222-2222-222222222222', 'a2b3c4d5-e6f7-4901-2345-67890abcdef1', '5cf1e66d-4261-4bad-92bb-4e30f1cde8c3', 'Beta Chat')
ON CONFLICT (id) DO UPDATE SET
  tenant_id = EXCLUDED.tenant_id,
  owner_user_id = EXCLUDED.owner_user_id,
  title = EXCLUDED.title;
