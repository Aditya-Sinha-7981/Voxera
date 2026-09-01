# Supabase migrations

Apply in order:

```
psql "$SUPABASE_DB_URL" -f migrations/001_initial_schema.sql
```

Or via the Supabase CLI:

```
supabase db reset    # local
supabase db push     # linked remote project
```
