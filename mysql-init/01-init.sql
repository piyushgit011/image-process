-- MySQL Initialization Script for Image Processing Pipeline
-- This script runs automatically when the MySQL container starts for the first time

USE image_processing;

-- Create indexes for better performance (if table exists)
-- Note: The table will be created by the application's database_models.py
-- These indexes will be created after the application initializes the schema

-- Create a procedure to add indexes if the table exists
DELIMITER //
CREATE PROCEDURE CreateIndexesIfTableExists()
BEGIN
    DECLARE table_count INT DEFAULT 0;
    
    -- Check if the processed_images table exists
    SELECT COUNT(*) INTO table_count 
    FROM information_schema.tables 
    WHERE table_schema = 'image_processing' 
    AND table_name = 'processed_images';
    
    -- If table exists, create indexes
    IF table_count > 0 THEN
        -- Create indexes for better query performance
        SET @sql = 'CREATE INDEX IF NOT EXISTS idx_processed_images_job_id ON processed_images(job_id)';
        PREPARE stmt FROM @sql;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
        
        SET @sql = 'CREATE INDEX IF NOT EXISTS idx_processed_images_created_at ON processed_images(created_at)';
        PREPARE stmt FROM @sql;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
        
        SET @sql = 'CREATE INDEX IF NOT EXISTS idx_processed_images_vehicle_detected ON processed_images(is_vehicle_detected)';
        PREPARE stmt FROM @sql;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
        
        SET @sql = 'CREATE INDEX IF NOT EXISTS idx_processed_images_face_detected ON processed_images(is_face_detected)';
        PREPARE stmt FROM @sql;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
        
        SET @sql = 'CREATE INDEX IF NOT EXISTS idx_processed_images_face_blurred ON processed_images(is_face_blurred)';
        PREPARE stmt FROM @sql;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
        
        -- Create a view for statistics
        SET @sql = 'CREATE VIEW IF NOT EXISTS processing_statistics AS
        SELECT 
            COUNT(*) as total_images,
            SUM(is_vehicle_detected) as vehicles_detected,
            SUM(is_face_detected) as faces_detected,
            SUM(is_face_blurred) as faces_blurred,
            ROUND(AVG(processing_time_seconds), 2) as avg_processing_time,
            DATE(created_at) as processing_date
        FROM processed_images
        GROUP BY DATE(created_at)
        ORDER BY processing_date DESC';
        PREPARE stmt FROM @sql;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
    END IF;
END //
DELIMITER ;

-- Note: The procedure will be called by the application after table creation
-- This ensures proper initialization order

-- Set MySQL configuration for better performance
SET GLOBAL innodb_buffer_pool_size = 1073741824; -- 1GB
SET GLOBAL max_connections = 200;
SET GLOBAL wait_timeout = 28800;
SET GLOBAL interactive_timeout = 28800;

-- Enable slow query log for monitoring
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 2;

-- Optimize for InnoDB
SET GLOBAL innodb_flush_log_at_trx_commit = 2;
SET GLOBAL innodb_flush_method = 'O_DIRECT';

-- Create a user for monitoring (optional)
CREATE USER IF NOT EXISTS 'monitor'@'%' IDENTIFIED BY 'monitor_password';
GRANT PROCESS, REPLICATION CLIENT ON *.* TO 'monitor'@'%';
GRANT SELECT ON performance_schema.* TO 'monitor'@'%';
FLUSH PRIVILEGES;

-- Log initialization completion
SELECT 'MySQL initialization completed for Image Processing Pipeline' AS status;