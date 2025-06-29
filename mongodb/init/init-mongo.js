// MongoDB initialization script for Chat with Data application

// Switch to the chat database
db = db.getSiblingDB('chatdb');

// Create collections with validation schemas
db.createCollection('sessions', {
    validator: {
        $jsonSchema: {
            bsonType: 'object',
            required: ['session_id', 'created_at', 'last_activity'],
            properties: {
                session_id: {
                    bsonType: 'string',
                    description: 'Unique session identifier'
                },
                created_at: {
                    bsonType: 'date',
                    description: 'Session creation timestamp'
                },
                last_activity: {
                    bsonType: 'date',
                    description: 'Last activity timestamp'
                },
                user_id: {
                    bsonType: ['string', 'null'],
                    description: 'Optional user identifier'
                },
                data_source: {
                    bsonType: ['object', 'null'],
                    description: 'Connected data source information'
                },
                message_count: {
                    bsonType: 'int',
                    minimum: 0,
                    description: 'Number of messages in session'
                },
                metadata: {
                    bsonType: 'object',
                    description: 'Additional session metadata'
                }
            }
        }
    }
});

db.createCollection('messages', {
    validator: {
        $jsonSchema: {
            bsonType: 'object',
            required: ['session_id', 'role', 'content', 'timestamp'],
            properties: {
                session_id: {
                    bsonType: 'string',
                    description: 'Session identifier'
                },
                role: {
                    bsonType: 'string',
                    enum: ['user', 'assistant', 'system'],
                    description: 'Message role'
                },
                content: {
                    bsonType: 'string',
                    description: 'Message content'
                },
                timestamp: {
                    bsonType: 'date',
                    description: 'Message timestamp'
                },
                metadata: {
                    bsonType: 'object',
                    description: 'Additional message metadata'
                }
            }
        }
    }
});

db.createCollection('query_history', {
    validator: {
        $jsonSchema: {
            bsonType: 'object',
            required: ['session_id', 'query', 'timestamp'],
            properties: {
                session_id: {
                    bsonType: 'string',
                    description: 'Session identifier'
                },
                query: {
                    bsonType: 'string',
                    description: 'Executed query'
                },
                query_hash: {
                    bsonType: ['long', 'int'],
                    description: 'Query hash for deduplication'
                },
                execution_time: {
                    bsonType: 'double',
                    minimum: 0,
                    description: 'Query execution time in seconds'
                },
                result_count: {
                    bsonType: 'int',
                    minimum: 0,
                    description: 'Number of results returned'
                },
                timestamp: {
                    bsonType: 'date',
                    description: 'Query execution timestamp'
                },
                status: {
                    bsonType: 'string',
                    enum: ['success', 'error', 'timeout'],
                    description: 'Query execution status'
                }
            }
        }
    }
});

db.createCollection('file_metadata', {
    validator: {
        $jsonSchema: {
            bsonType: 'object',
            required: ['file_id', 'filename', 'upload_time'],
            properties: {
                file_id: {
                    bsonType: 'string',
                    description: 'Unique file identifier'
                },
                filename: {
                    bsonType: 'string',
                    description: 'Original filename'
                },
                file_type: {
                    bsonType: 'string',
                    description: 'File type/extension'
                },
                file_size: {
                    bsonType: 'long',
                    minimum: 0,
                    description: 'File size in bytes'
                },
                upload_time: {
                    bsonType: 'date',
                    description: 'File upload timestamp'
                },
                rows: {
                    bsonType: 'int',
                    minimum: 0,
                    description: 'Number of rows in dataset'
                },
                columns: {
                    bsonType: 'int',
                    minimum: 0,
                    description: 'Number of columns in dataset'
                },
                column_info: {
                    bsonType: 'array',
                    description: 'Column metadata'
                },
                is_sample: {
                    bsonType: 'bool',
                    description: 'Whether this is a sample dataset'
                }
            }
        }
    }
});

// Create indexes for better performance
db.sessions.createIndex({ session_id: 1 }, { unique: true });
db.sessions.createIndex({ created_at: 1 });
db.sessions.createIndex({ last_activity: 1 });
db.sessions.createIndex({ user_id: 1 });

db.messages.createIndex({ session_id: 1, timestamp: 1 });
db.messages.createIndex({ timestamp: 1 });
db.messages.createIndex({ role: 1 });

db.query_history.createIndex({ session_id: 1, timestamp: 1 });
db.query_history.createIndex({ query_hash: 1 });
db.query_history.createIndex({ timestamp: 1 });
db.query_history.createIndex({ status: 1 });

db.file_metadata.createIndex({ file_id: 1 }, { unique: true });
db.file_metadata.createIndex({ upload_time: 1 });
db.file_metadata.createIndex({ file_type: 1 });

// Create a user for the application
db.createUser({
    user: 'chatapp',
    pwd: 'chatapp123',
    roles: [
        {
            role: 'readWrite',
            db: 'chatdb'
        }
    ]
});

// Insert some initial data for testing
db.sessions.insertOne({
    session_id: 'test_session_001',
    created_at: new Date(),
    last_activity: new Date(),
    user_id: null,
    data_source: null,
    message_count: 0,
    metadata: {
        created_by: 'init_script',
        version: '1.0'
    }
});

print('✅ MongoDB initialization completed successfully');
print('📊 Database: chatdb');
print('👤 User: chatapp created');
print('📋 Collections created with indexes');
print('🔧 Ready for Chat with Data application'); 