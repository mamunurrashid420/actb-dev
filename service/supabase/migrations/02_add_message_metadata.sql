-- Migration to add metadata column for storing rich message content as JSONB

-- Add metadata column to messages table
ALTER TABLE messages
ADD COLUMN IF NOT EXISTS metadata JSONB;

-- Create index on metadata for better query performance
CREATE INDEX IF NOT EXISTS idx_messages_metadata ON messages USING gin(metadata);

-- Add comment to explain the column
COMMENT ON COLUMN messages.metadata IS 'Stores rich message content (charts, buttons, etc.) as JSONB';
