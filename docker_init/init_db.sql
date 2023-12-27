-- create table users
CREATE TABLE IF NOT EXISTS `users`
(
    `user_id`       int(11) AUTO_INCREMENT PRIMARY KEY,
    `user_email`    VARCHAR(255) DEFAULT NULL,
    `user_username` VARCHAR(255) NOT NULL,
    `user_password` VARCHAR(255) NOT NULL
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_general_ci;

-- create user security table --
CREATE TABLE IF NOT EXISTS `user_security`
(
    `user_security_id`      int(11) AUTO_INCREMENT PRIMARY KEY,
    `user_id`               int(11)    NOT NULL,
    `is_active`             tinyint(4) NOT NULL DEFAULT 1,
    `last_login_date`       bigint(20) NOT NULL,
    `failed_login_attempts` int(11)    NOT NULL DEFAULT 0,
    `account_locked_until`  bigint(20) NOT NULL DEFAULT 0,
    FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_general_ci;

-- create radio system table
CREATE TABLE IF NOT EXISTS `radio_systems`
(
    `system_id`      int(11) AUTO_INCREMENT PRIMARY KEY,
    `system_name`    varchar(255) DEFAULT NULL,
    `system_county`  varchar(255) DEFAULT NULL,
    `system_state`  varchar(255) DEFAULT NULL,
    `system_fips`    int(11)      DEFAULT NULL,
    `system_api_key` varchar(64) DEFAULT NULL
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_general_ci;

-- create agencies table
CREATE TABLE IF NOT EXISTS `agencies`
(
    `agency_id`                 int(11) AUTO_INCREMENT PRIMARY KEY,
    `system_id`                 int(11)       NOT NULL,
    `agency_code`               varchar(128)           DEFAULT NULL,
    `agency_name`               varchar(255)           NOT NULL,
    `alert_email_subject`       varchar(512)           NOT NULL DEFAULT 'Dispatch Alert - {detector_name}',
    `alert_email_body`          text                   DEFAULT NULL,
    `mqtt_topic`                varchar(255)           DEFAULT NULL,
    `mqtt_start_alert_message`  varchar(255)           NOT NULL DEFAULT 'on',
    `mqtt_end_alert_message`    varchar(255)           NOT NULL DEFAULT 'off',
    `mqtt_message_interval`     decimal(6, 1) NOT NULL DEFAULT 5.0,
    `pushover_group_token`      varchar(255)  DEFAULT NULL,
    `pushover_app_token`        varchar(255)  DEFAULT NULL,
    `pushover_subject_override` varchar(512)           DEFAULT NULL,
    `pushover_body_override`    text                   DEFAULT NULL,
    `pushover_sound_override`   varchar(128)           DEFAULT NULL,
    `agency_stream_url`         varchar(512)  DEFAULT NULL,
    `enable_facebook_post`      tinyint(1)    NOT NULL DEFAULT 0,
    FOREIGN KEY (`system_id`) REFERENCES `radio_systems` (`system_id`) ON DELETE CASCADE
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_general_ci;

-- Agency Emails
CREATE TABLE IF NOT EXISTS `agency_emails`
(
    `agency_email_id` int(11)      NOT NULL,
    `agency_id`       int(11)      NOT NULL,
    `email_address`   varchar(255) NOT NULL,
    FOREIGN KEY (`agency_id`) REFERENCES `agencies` (`agency_id`) ON DELETE CASCADE
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_general_ci;

-- QuickCall Detectors
CREATE TABLE IF NOT EXISTS `qc_detectors`
(
    `detector_id`    int(11) AUTO_INCREMENT PRIMARY KEY,
    `agency_id`      int(11)       NOT NULL,
    `a_tone`         decimal(6, 1)          DEFAULT NULL,
    `b_tone`         decimal(6, 1)          DEFAULT NULL,
    `tone_tolerance` int(11)       NOT NULL DEFAULT 2,
    `ignore_time`    decimal(6, 1) NOT NULL DEFAULT 120.0,
    FOREIGN KEY (`agency_id`) REFERENCES `agencies` (`agency_id`) ON DELETE CASCADE
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_general_ci;


-- create table radio_transmissions
CREATE TABLE IF NOT EXISTS `radio_transmissions`
(
    `transmission_id`            VARCHAR(255)   NOT NULL,
    `system_id`                  INT(11)        NOT NULL,
    `talkgroup_decimal`          INT(11)        NOT NULL,
    `talkgroup_alpha_tag`        VARCHAR(255)   NOT NULL,
    `talkgroup_name`             VARCHAR(255)   NOT NULL,
    `audio_path`                 VARCHAR(512)   NOT NULL,
    `transmission_transcription` TEXT DEFAULT NULL,
    `transmission_duration`      DECIMAL(10, 2) NOT NULL,
    `transmission_timestamp`     BIGINT(20)     NOT NULL,
    PRIMARY KEY (`transmission_id`),
    FOREIGN KEY (`system_id`) REFERENCES `radio_systems` (`system_id`) ON DELETE CASCADE,
    INDEX `idx_talkgroup_decimal` (`talkgroup_decimal`),
    INDEX `idx_transmission_timestamp` (`transmission_timestamp`)

) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS `quickcall_tones`
(
    `quickcall_id`    INT(11) AUTO_INCREMENT PRIMARY KEY,
    `transmission_id` VARCHAR(255) NOT NULL,
    `exact_tone_a`    DECIMAL(10, 2),
    `exact_tone_b`    DECIMAL(10, 2),
    `actual_tone_a`   DECIMAL(10, 2),
    `actual_tone_b`   DECIMAL(10, 2),
    `occurred`        DECIMAL(10, 2),
    FOREIGN KEY (`transmission_id`) REFERENCES `radio_transmissions` (`transmission_id`) ON DELETE CASCADE
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS `long_tones`
(
    `long_tone_id`    INT(11) AUTO_INCREMENT PRIMARY KEY,
    `transmission_id` VARCHAR(255) NOT NULL,
    `actual_tone`     DECIMAL(10, 2),
    `occurred`        DECIMAL(10, 2),
    FOREIGN KEY (`transmission_id`) REFERENCES `radio_transmissions` (`transmission_id`) ON DELETE CASCADE
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS `hi_low_tones`
(
    `hi_low_tone_id`  INT(11) AUTO_INCREMENT PRIMARY KEY,
    `transmission_id` VARCHAR(255) NOT NULL,
    `actual_tone_a`   DECIMAL(10, 2),
    `actual_tone_b`   DECIMAL(10, 2),
    `occurred`        DECIMAL(10, 2),
    FOREIGN KEY (`transmission_id`) REFERENCES `radio_transmissions` (`transmission_id`) ON DELETE CASCADE
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS `dtmf_tones`
(
    `dtmf_id`         INT(11) AUTO_INCREMENT PRIMARY KEY,
    `transmission_id` VARCHAR(255) NOT NULL,
    `keys`            VARCHAR(512),
    `occurred`        DECIMAL(10, 2),
    FOREIGN KEY (`transmission_id`) REFERENCES `radio_transmissions` (`transmission_id`) ON DELETE CASCADE
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS `quickcall_matches`
(
    `quickcall_match_id` INT(11) AUTO_INCREMENT PRIMARY KEY,
    `quickcall_id`       INT(11)      NOT NULL,
    `detector_id`        INT(11)      NOT NULL,
    `detector_name`      VARCHAR(255) NOT NULL,
    `a_tone`             DECIMAL(10, 2),
    `b_tone`             DECIMAL(10, 2),
    `ignored`            TINYINT(1) DEFAULT 0,
    FOREIGN KEY (`quickcall_id`) REFERENCES `quickcall_tones` (`quickcall_id`) ON DELETE CASCADE,
    FOREIGN KEY (`detector_id`) REFERENCES `qc_detectors` (`detector_id`) ON DELETE CASCADE
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_general_ci;

-- enable event scheduler
SET GLOBAL event_scheduler = ON;

-- create event to delete old transmissions
CREATE EVENT IF NOT EXISTS `prune_radio_transmissions`
    ON SCHEDULE EVERY 1 DAY
        STARTS (TIMESTAMP(CURRENT_DATE) + INTERVAL 1 DAY)
    DO
    DELETE
    FROM `radio_transmissions`
    WHERE `transmission_timestamp` < UNIX_TIMESTAMP(CURRENT_DATE - INTERVAL 14 DAY);