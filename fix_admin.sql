-- Add account type 7 if not exists
INSERT INTO data.type_account (id, title) VALUES (7, 'Администратор') ON CONFLICT (id) DO UPDATE SET title = EXCLUDED.title;

-- Get admin user ID and add type 7
DO $$
DECLARE
    admin_user_id INTEGER;
BEGIN
    SELECT id INTO admin_user_id FROM users."user" WHERE phone = '+79995555555';
    
    IF admin_user_id IS NOT NULL THEN
        -- Add type 7 for admin
        INSERT INTO authentication.user_account (id_user, id_type_account)
        VALUES (admin_user_id, 7)
        ON CONFLICT DO NOTHING;
        
        RAISE NOTICE 'Admin user % updated with type 7', admin_user_id;
    ELSE
        RAISE NOTICE 'Admin user not found';
    END IF;
END $$;
