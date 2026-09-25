-- MySQL dump 10.13  Distrib 8.0.44, for Win64 (x86_64)
--
-- Host: trolley.proxy.rlwy.net    Database: railway
-- ------------------------------------------------------
-- Server version	9.4.0

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `audit_logs`
--

DROP TABLE IF EXISTS `audit_logs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_logs` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `user_id` int unsigned DEFAULT NULL,
  `username` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `action` varchar(80) COLLATE utf8mb4_unicode_ci NOT NULL,
  `item` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_audit_logs_created_at` (`created_at`),
  KEY `idx_audit_logs_user_id` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `audit_logs`
--

LOCK TABLES `audit_logs` WRITE;
/*!40000 ALTER TABLE `audit_logs` DISABLE KEYS */;
/*!40000 ALTER TABLE `audit_logs` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `events`
--

DROP TABLE IF EXISTS `events`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `events` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `user_id` int unsigned NOT NULL,
  `name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `event_date` date NOT NULL,
  `event_type` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'event',
  `share_token` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_starred` tinyint(1) NOT NULL DEFAULT '0',
  `is_deleted` tinyint(1) NOT NULL DEFAULT '0',
  `deleted_at` timestamp NULL DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_events_share_token` (`share_token`),
  KEY `idx_events_user` (`user_id`,`is_deleted`,`event_date`),
  CONSTRAINT `fk_events_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `events`
--

LOCK TABLES `events` WRITE;
/*!40000 ALTER TABLE `events` DISABLE KEYS */;
INSERT INTO `events` VALUES (1,4,'Youth_KAPEllowship','2026-08-15','fellowship','5682206c9e2e11f1bf5940c2ba07daba',0,0,NULL,'2026-08-25 12:38:38','2026-08-26 06:57:37');
/*!40000 ALTER TABLE `events` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `files`
--

DROP TABLE IF EXISTS `files`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `files` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `user_id` int unsigned NOT NULL,
  `original_filename` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `stored_filename` varchar(320) COLLATE utf8mb4_unicode_ci NOT NULL,
  `file_size` bigint unsigned NOT NULL,
  `mime_type` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `share_token` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `folder_id` int unsigned DEFAULT NULL,
  `event_id` int unsigned DEFAULT NULL,
  `original_folder_id` int unsigned DEFAULT NULL,
  `is_starred` tinyint(1) NOT NULL DEFAULT '0',
  `is_deleted` tinyint(1) NOT NULL DEFAULT '0',
  `deleted_at` timestamp NULL DEFAULT NULL,
  `uploaded_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `accessed_at` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_files_stored_filename` (`stored_filename`),
  UNIQUE KEY `uq_files_share_token` (`share_token`),
  KEY `idx_files_user_uploaded` (`user_id`,`uploaded_at`),
  KEY `idx_files_user_folder` (`user_id`,`folder_id`,`is_deleted`),
  KEY `idx_files_user_event` (`user_id`,`event_id`,`is_deleted`),
  KEY `fk_files_folder` (`folder_id`),
  CONSTRAINT `fk_files_folder` FOREIGN KEY (`folder_id`) REFERENCES `folders` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_files_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=76 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `files`
--

LOCK TABLES `files` WRITE;
/*!40000 ALTER TABLE `files` DISABLE KEYS */;
INSERT INTO `files` VALUES (1,4,'Untitled_design.png','0c4254ca296448329a053974a9a8eee8_Untitled_design.png',869703,'image/png','DSgTtLOERFloEk6FwvXaBCLwwu_p6SzWL349t-iL4dc',NULL,NULL,NULL,0,0,NULL,'2026-08-19 08:50:48','2026-08-26 07:21:05'),(2,4,'79eafa7bbd24e733a206a071e87adb32.jpg','5008837248a94de1bd04a85958fe47d4_79eafa7bbd24e733a206a071e87adb32.jpg',58051,'image/jpeg','U-HUnhky5UY0Tgi3q0F7fk76AYkB6dttWlAJxQlSmSw',NULL,NULL,NULL,0,0,NULL,'2026-08-19 08:50:48','2026-08-26 05:37:23'),(3,4,'Week02_CMSC305_Seatwork2.docx','50b8658879c54e6fa3907438405e073b_Week02_CMSC305_Seatwork2.docx',485281,'application/vnd.openxmlformats-officedocument.wordprocessingml.document','uXAdr5XFZZ4DgLxh764MF_D4A-HuOxq98yjS3Tqkngk',NULL,NULL,NULL,0,0,NULL,'2026-08-19 08:50:48','2026-08-26 05:37:29'),(4,4,'Week03_CMSC306_Lab_Experiment_02_Subtractor_Circuit.docx','6fd772c1024e41c28713784db6321c80_Week03_CMSC306_Lab_Experiment_02_Subtractor_Circuit.docx',499548,'application/vnd.openxmlformats-officedocument.wordprocessingml.document','D3N55I5oYNKt_hoWu3SbQfaLDOhyzoRoiCU7zwLz8Yw',NULL,NULL,NULL,0,0,NULL,'2026-08-19 08:50:48',NULL),(5,4,'Joshua_Duenas_-_Resume.pdf','f47e3ab9355a4c81a06df2c21b77f0c0_Joshua_Duenas_-_Resume.pdf',106374,'application/pdf','lrkdLg_ZixdUYklSVn9F9B4BeZDrHwffj1iXCDwD650',NULL,NULL,NULL,0,0,NULL,'2026-08-19 08:50:48',NULL),(6,4,'tinytask.ini','077f2953b2504d369af8e3189b2b6570_tinytask.ini',138,'application/octet-stream','gQma_bHjjs8ccHQxGAaAOURv-LqFPZk80Jzk3kTnZlw',1,NULL,NULL,0,0,NULL,'2026-08-19 10:04:52','2026-09-23 05:46:57'),(7,4,'57-579715_snoopy-sleeping-png-snoopy-sleeping-clip-art-snoopy.png','b3e01470109c4d55bf5a3e61e682b634_57-579715_snoopy-sleeping-png-snoopy-sleeping-clip-art-snoopy.png',626833,'image/png','f0i27kWBlQ4AJVPXmtYjZaFSY_P4LKzKNDG4V7my_GY',NULL,NULL,NULL,0,0,NULL,'2026-08-19 10:04:52','2026-09-23 05:47:07'),(8,4,'FINAL-REQUIREMENTS-CHECKLIST-2025.pdf','6689ebb53bc24c49860fb8eda25c9a3a_FINAL-REQUIREMENTS-CHECKLIST-2025.pdf',81428,'application/pdf','-1TFE2hGtMCVllS3HajsjoRLdv6oTS0QECphIP2TQkM',NULL,NULL,NULL,0,0,NULL,'2026-08-19 10:04:52',NULL),(10,4,'A_Comparative_Analysis_of_the_Problems_Experienced_by_Senior_High_School_Students_of_San_Antonio_de_Padua_College_Foundation_Pila_Laguna_School_Years_20242025_and_20252026__Basis_for_an_Intervention_Program_1.pdf','38819f72478a4ec8b99ff0e5ca7b2be5_A_Comparative_Analysis_of_the_Problems_Experienced_by_Senior_High_School_Students_of_San_Antonio_de_Padua_College_Foundation_Pila_Laguna_School_Years_20242025_and_20252026__Basis_for_an_Intervention_Program_1.pdf',2115635,'application/pdf','_KKNePBtvz0ABBm8NS5hD7KJdz0l4Ygul0AbNg2hkMI',NULL,NULL,NULL,1,0,NULL,'2026-08-19 10:04:52','2026-08-21 10:36:03'),(11,4,'JF_Pila_-_Youth.xlsx','4932497c59954c76806a4d031f0417db_JF_Pila_-_Youth.xlsx',301824,'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet','0uUfK0-uCZuDRQXGPSd7k-JLEU7jmem0gg3oGXF3fJo',NULL,NULL,NULL,0,0,NULL,'2026-08-20 05:17:05','2026-09-23 05:47:03'),(13,4,'app.js','ed788a7177914c4282364a6f65f8ed35_app.js',38147,'text/javascript','Za8RTsXWo9C2WOjynCUVsFCdS38pMU1x9sk1JI2NqZc',NULL,NULL,NULL,0,0,NULL,'2026-08-20 10:43:03','2026-08-22 15:04:58'),(14,4,'Audio.png','d91d7e5254a44d568a46bdc0044db9b0_Audio.png',682,'image/png','56hSnqg1LqW31h_FsMO_0LV-nRbqKZGHuO-kMEucYJg',4,NULL,4,0,1,'2026-09-23 10:15:13','2026-08-20 10:45:20',NULL),(15,4,'CLOSE.png','617d0a4d0baf4ab9b9bcf900ce959f8d_CLOSE.png',1065,'image/png','tiTjzWDaFQZ2yAj7rAvIOYCdqlN5IN7HdhvCRDLraow',4,NULL,4,0,1,'2026-09-23 10:15:02','2026-08-20 10:45:20',NULL),(16,4,'CLOSE_hover.png','b92259051772430ebad3a6c1fefa3b05_CLOSE_hover.png',1059,'image/png','pVgdxfYXVKzPNfVd7A2f7uOTi_JxIWUH0RwkoD55jkQ',4,NULL,4,0,1,'2026-09-23 10:15:02','2026-08-20 10:45:20',NULL),(17,4,'CPL.png','3c2ed86b4ddb48a691a2395dea9ab734_CPL.png',2340,'image/png','JjqPY-NRTiqa7KD9oMv4MR7tOw9skY6MMhOJutb3690',4,NULL,4,0,1,'2026-09-23 10:15:02','2026-08-20 10:45:20',NULL),(18,4,'CPL_hover.png','1715556147414563801d889c47724f51_CPL_hover.png',2818,'image/png','AhmapnWb_B36OfBC1uGXjz98OCCKHyhwIt0fvPwgSo8',4,NULL,4,0,1,'2026-09-23 10:15:02','2026-08-20 10:45:20',NULL),(19,4,'DEL.png','d7080423da8442b5a25852f5e7f1f5a0_DEL.png',1917,'image/png','CY6hQfJG-kBQ4tbTXuFNMy8jKeNPJa1zi1C7WjZVYU8',4,NULL,4,0,1,'2026-09-23 10:15:02','2026-08-20 10:45:20',NULL),(20,4,'DEL_hover.png','c7db4e1092164464908ca56e267d3fd7_DEL_hover.png',1924,'image/png','vXiWDhyhrDvc8VTya0J1eeERtvX50QVlpWTKMpuklrg',4,NULL,4,0,1,'2026-09-23 10:15:02','2026-08-20 10:45:20',NULL),(21,4,'DL.png','76d2d3d41ecd4a7cb8379ff982714fdc_DL.png',2500,'image/png','HOXb__trVIzQfVsW_UtqY9KFP9AuVzmtC__Srw8K-aU',4,NULL,4,0,1,'2026-09-23 10:15:02','2026-08-20 10:45:20',NULL),(22,4,'DLfile.png','8c7df437b94341938d73eddcb42b90f8_DLfile.png',2791,'image/png','RQb3ACM8jGN_8npuVDG-pwr9eMaaZj4vcXlwG2XthR4',4,NULL,4,0,1,'2026-09-23 10:15:02','2026-08-20 10:45:20',NULL),(23,4,'DLfile_hover.png','fbf2cc01459b453a903189f03280274c_DLfile_hover.png',2814,'image/png','NjXzp8oUj2tz2a7eyr66oGeU7cHsjRvwAqo64h5o14s',4,NULL,4,0,1,'2026-09-23 10:15:02','2026-08-20 10:45:20',NULL),(24,4,'DL_hover.png','a66480db976e431c99e069bab66cca7b_DL_hover.png',2466,'image/png','wmtxNZl3ayeD55fH_6U360HSpWTOR7HDn5TTDxIRg1g',4,NULL,4,0,1,'2026-09-23 10:15:02','2026-08-20 10:45:20',NULL),(25,4,'File.png','25ffa512bbfd4aecbf6b5b13555ccf2f_File.png',560,'image/png','Skcc04Au8IDUzcPrawihO820IR0_Wvd5LDJcpHamXKs',4,NULL,4,0,1,'2026-09-23 10:15:02','2026-08-20 10:45:20',NULL),(26,4,'FL.png','190909ec4aa64f7084eac10fd44e8527_FL.png',1707,'image/png','V3N7RqHC0FOHTbyo6UgOCYOuCkiHWG_qZuU8YRmDH6w',4,NULL,4,0,1,'2026-09-23 10:15:02','2026-08-20 10:45:20',NULL),(27,4,'FL_hover.png','69d9196822364c9383b55a0545908585_FL_hover.png',1707,'image/png','ohd53__6RiyMGKqHl_m3cB35zOk22eTyT4t0y58dnIg',4,NULL,4,0,1,'2026-09-23 10:15:02','2026-08-20 10:45:20',NULL),(28,4,'Folder.png','3834f0635fd84291b61ad549fd0f7126_Folder.png',426,'image/png','QpBvmApwu4kkLfSMQI2yoDJY1aaG5UMIatP4B94RVHQ',4,NULL,4,0,1,'2026-09-23 10:15:13','2026-08-20 10:45:20',NULL),(29,4,'Image.png','3efcd7a1a45e40c5b0c3fec439718023_Image.png',542,'image/png','7POLZQDu7N0d0-BpMJM_WpuHeoHIGBImcBE9YMAREVY',4,NULL,4,0,1,'2026-09-23 10:15:13','2026-08-20 10:45:20',NULL),(30,4,'JF.ico','96dd2cb5e6d2481c920db132615559ab_JF.ico',4022,'image/x-icon','JL4qQCzhmbIc0BTz1CxiC11gX9Frcjq0jW6Nu_2dxGY',4,NULL,4,0,1,'2026-09-23 10:15:02','2026-08-20 10:45:20',NULL),(31,4,'JF.png','858efcb719194c2cb4a7f81ab77e73d8_JF.png',26404,'image/png','PUBeXFUy-0DF60xUiMIsAl5S-mklmIX9xbID0imziBs',4,NULL,4,0,1,'2026-09-23 10:15:02','2026-08-20 10:45:20',NULL),(32,4,'jfcm.png','967745206a844e5885feb2470a20c746_jfcm.png',81616,'image/png','89PFVEoVK2Yl7RGmPYEcOFPpXzUnzxZVVz17_KXX4bw',4,NULL,4,0,1,'2026-09-23 10:15:02','2026-08-20 10:45:20',NULL),(33,4,'mingcute_pdf-fill.png','df7bbe7321be438e8937fe691f2baec7_mingcute_pdf-fill.png',688,'image/png','k5Gx8oIaiGQFyyNFqnxcEbGpSHoU8F9J-EXTNQFBQyw',4,NULL,4,0,1,'2026-09-23 10:15:02','2026-08-20 10:45:20','2026-09-23 10:14:26'),(34,4,'PDF.png','fc223bdd4254485094575676010631c9_PDF.png',1042,'image/png','brTnOxByu--UG84Oe0M41lnJnggbuw1runXICEjXijc',4,NULL,4,0,1,'2026-09-23 10:15:02','2026-08-20 10:45:20',NULL),(35,4,'PPT.png','0fcabe3b149f49aeaeb8d5efc5bbde20_PPT.png',758,'image/png','Yd-XCVBDATDAFxZQB7iJCaiznJ0FshebbvpUj6bv4hc',4,NULL,4,0,1,'2026-09-23 10:15:02','2026-08-20 10:45:20',NULL),(36,4,'reicon_audio-square-filled.png','95af24fae592433abb226bec037be218_reicon_audio-square-filled.png',917,'image/png','uFrsPISbt6spwrttZE6Z7xhGiEjBPHVCHxD4YTdrsr4',4,NULL,4,0,1,'2026-09-23 10:15:02','2026-08-20 10:45:20',NULL),(37,4,'reicon_doc-text-filled.png','ccbdcb9967d04003a9b4347002c152de_reicon_doc-text-filled.png',680,'image/png','x8_DH4f4LIfmYNddtLwqQohZj3GsYPEDWmxMap5eCN4',4,NULL,4,0,1,'2026-09-23 10:15:02','2026-08-20 10:45:20',NULL),(38,4,'RN.png','f9a2c68f88c3454fab92d3f605e2ef41_RN.png',2312,'image/png','yfu7lUl5koV1n5lOAYxt5AISd-_Hao0XOL9gBEYTWQ8',4,NULL,4,0,1,'2026-09-23 10:15:02','2026-08-20 10:45:20',NULL),(39,4,'RN_hover.png','48fe36e57d8844d1b0c73f70b7c5b309_RN_hover.png',2392,'image/png','eqqnjcHvFOxoKJHtDwl709TG2gjMujULV_dNFeZzf9E',4,NULL,4,0,1,'2026-09-23 10:15:13','2026-08-20 10:45:20',NULL),(40,4,'solar_file-bold.png','60190392c2ae4fa0835af4b9ffd27546_solar_file-bold.png',742,'image/png','0-QYG9WMlJNgsi0bbRyxu_rUdME7PAuyvTa8ujU31s4',4,NULL,4,0,1,'2026-09-23 10:15:13','2026-08-20 10:45:20',NULL),(41,4,'Spreadsheet.png','cd67bfebdb264017bb33beb8e55c063e_Spreadsheet.png',589,'image/png','tnMG3d17qBwoqQi3mr4fVjB2efu9SvSfZlZVB9d3smY',4,NULL,4,0,1,'2026-09-23 10:15:14','2026-08-20 10:45:20',NULL),(42,4,'Video.png','5ce7a8b18c1049e38aab099664dd6c55_Video.png',587,'image/png','RoXByH1XtwY9jeNlsFDTNVG3G1N8nUegoqrIcdJklWs',4,NULL,4,0,1,'2026-09-23 10:15:14','2026-08-20 10:45:20',NULL),(43,4,'VW.png','7f542f59adea42f487d9944f6bd33855_VW.png',2141,'image/png','qgTRYqSspPumxbOKXszsXjkTJiI4jXYCUxpK2WNP0qc',4,NULL,4,0,1,'2026-09-23 10:15:14','2026-08-20 10:45:20',NULL),(44,4,'VW_hover.png','f0e980ff480c48eda6ae65706bca83e2_VW_hover.png',2665,'image/png','gxapCUuaG7sNznjPaFtMOxHroJdYHancGe_QvneXgi8',4,NULL,4,0,1,'2026-09-23 10:15:14','2026-08-20 10:45:20','2026-09-23 10:14:50'),(45,4,'Word.png','29d9047c94b14e84b3227db0610859dd_Word.png',791,'image/png','BS7cqsB5JFQNEZ-jJgdFfC5-l4dGN14wm2Ei1ojpfoU',4,NULL,4,0,1,'2026-09-23 10:15:02','2026-08-20 10:45:20',NULL),(46,4,'frank-ocean-blond-music-rjr51ik7cbd17sgb.jpg','0a5d6ca3005841828ff515abcb107db3_frank-ocean-blond-music-rjr51ik7cbd17sgb.jpg',251638,'image/jpeg','eRVo16rgxfmJztGkjCeD2z-cjC_ZBbUdVYqzeB0YbtE',NULL,NULL,NULL,0,0,NULL,'2026-08-20 15:59:18','2026-09-23 22:27:34'),(47,4,'maxresdefault.jpg','f3a281a26ae74015a7eccc0f31fb2306_maxresdefault.jpg',73243,'image/jpeg','1t_Vf7KtHmGo2oioDtxkd_zl1gCrhRa83YbMOD39Kcs',4,NULL,4,0,1,'2026-09-23 10:15:02','2026-08-20 18:49:05',NULL),(48,4,'GELO.mp4','9ba4ebf419104b36a17bc44e02b2a001_GELO.mp4',2239947,'video/mp4','9ow0l_zGL3udIpjkVuX4SUvRd9H0nlflVOay3XXCqU0',NULL,NULL,NULL,0,0,NULL,'2026-08-26 07:13:16','2026-09-23 09:54:32'),(49,4,'Blue_White_Black_Modern_Clean_Pitch_Deck_Laundry_Presentation.pptx','7313edf69d1a43a1b09d8331412aa8da_Blue_White_Black_Modern_Clean_Pitch_Deck_Laundry_Presentation.pptx',7873460,'application/vnd.openxmlformats-officedocument.presentationml.presentation','aEDxNFh_YEgogRZWsf0_v__1uSpDHy5DfvzLT4mKOFc',NULL,1,NULL,0,0,NULL,'2026-09-23 06:05:57',NULL),(50,4,'All.png','c0001683b157481aa42644e134a8bbea_All.png',435,'image/png','WJhfabWwew2nB8npgZut537XpMX-l2g-CR6eIao5TI8',4,NULL,NULL,0,0,NULL,'2026-09-23 10:17:46',NULL),(51,4,'Audio.png','1989c940bf324f089e85b08ffb8c90ed_Audio.png',904,'image/png','1LZ3fDn60Uy7p7HvaP4MkynoJE-RZlCiIdKHlewFadM',4,NULL,NULL,0,0,NULL,'2026-09-23 10:17:46',NULL),(52,4,'Birthday.png','f85d450ef17a4b21bba9af3ff09fc699_Birthday.png',422061,'image/png','oQMI8TAFM00PykJV7yFZvIKKUXowm-zER8G5VrR3TkQ',4,NULL,NULL,0,0,NULL,'2026-09-23 10:17:47',NULL),(53,4,'Camp.png','f5def35a3e594f869a91968a2cb61675_Camp.png',429765,'image/png','EnxtkpGJKlLPtnk-cqLsTHFRbaappGdJjFXCu89bh_w',4,NULL,NULL,0,0,NULL,'2026-09-23 10:17:47',NULL),(54,4,'Celebration.png','b3933df29cb24a53ac5fb4a0e081fb1d_Celebration.png',513191,'image/png','dUdt8GduVqFga955n3qoxZxZ4UOrulYWYbSt8QncgRc',4,NULL,NULL,0,0,NULL,'2026-09-23 10:17:48',NULL),(55,4,'Conference.png','03a1cdb444b04c098959b75459a4a148_Conference.png',401340,'image/png','FcG86_1bb5e6LCHzwxq1Rk0ClhZQUsEdhShDoS2EmDI',4,NULL,NULL,0,0,NULL,'2026-09-23 10:17:48',NULL),(56,4,'Event.png','4a2785d991234ef3884a5d36c3509c9c_Event.png',687354,'image/png','lgEBwjUgHWO-xiyfSyGWSDdmiU0LnIqLXCY7932Aemo',4,NULL,NULL,0,0,NULL,'2026-09-23 10:17:49',NULL),(57,4,'Fellowship.png','fd92e8d006c746e6ac0d71965a15e1cc_Fellowship.png',507382,'image/png','c-HvIprvRfJPvWms5NKR_ZjHmYVRT9pG1vFFFihxvS0',4,NULL,NULL,0,0,NULL,'2026-09-23 10:17:49',NULL),(58,4,'File.png','0bd17df6465e41e0a51414ad620102e6_File.png',742,'image/png','huHBNgoEAutngrgZrxJcv4M98UlIwCtLxPnO_uaYj2Q',4,NULL,NULL,0,0,NULL,'2026-09-23 10:17:49',NULL),(59,4,'Folder.png','3e830316d9b64050b050523e67b8a36d_Folder.png',426,'image/png','UKKe1qpO33BeU4t5rvi0KAIExfkaI56opJTO3rFQFWE',4,NULL,NULL,0,0,NULL,'2026-09-23 10:17:49',NULL),(60,4,'Graduation.png','0fa4f0503fb6414390e236740655ed29_Graduation.png',523662,'image/png','ThthihvRW0ArwOs5xWHhdR9CA4ZpLWOUgqg-I0o6dnw',4,NULL,NULL,0,0,NULL,'2026-09-23 10:17:50',NULL),(61,4,'Heart.png','ab0d047fdaa644469358f3b879b20b8a_Heart.png',583762,'image/png','GWp88pP4PUsMQCQ5NR0SURxbI3HNYh1rQbuyFhsaVYM',4,NULL,NULL,0,0,NULL,'2026-09-23 10:17:50',NULL),(62,4,'Image.png','99d9e6dbceb44eec8e3b310062a04b5a_Image.png',542,'image/png','exBGUREqZfvcllUCCtovZHbxOBE7aKhTA9C2iiqgTxg',4,NULL,NULL,0,0,NULL,'2026-09-23 10:17:50',NULL),(63,4,'JF.ico','71e64204eaf443b5906259f8992c51f6_JF.ico',4022,'image/x-icon','IXSaaXW4fE3nS1DfRdZIy8EFKPOYVCxdFf3MAswEjO0',4,NULL,NULL,0,0,NULL,'2026-09-23 10:17:51',NULL),(64,4,'JF.png','6a96016221f543849494893dd30fb82b_JF.png',26404,'image/png','3F1E3a_Fs7LnuEQO6vk4jUUKzSf_XBZUuC7J334JDi0',4,NULL,NULL,0,0,NULL,'2026-09-23 10:17:51',NULL),(65,4,'PDF.png','3bc53b4488a6456bb294a4368b6686e6_PDF.png',714,'image/png','OjpnX6jNR8i5WX3HLgDXAVZVhZc8e2z4b0CzekAtyUY',4,NULL,NULL,0,0,NULL,'2026-09-23 10:17:51',NULL),(66,4,'PPT.png','32c6ca45c02144fea07dcd48ea6a9e83_PPT.png',826,'image/png','pXk-U2E27xnctYf0xwowXu8COINy0i99QND41IJQB1M',4,NULL,NULL,0,0,NULL,'2026-09-23 10:17:51',NULL),(67,4,'Spreadsheet.png','b9bd3691158540d4b5c37885657dc730_Spreadsheet.png',589,'image/png','Tjl_AmPei5YkNFTvL8N-sXJdRMKLrcv0XhHUdpSEPhk',4,NULL,NULL,0,0,NULL,'2026-09-23 10:17:52',NULL),(68,4,'ss.png','465cd4bcebe84cb288b904bfee842cd3_ss.png',106758,'image/png','2Wpon6nPoi5obaVUAK1GUkqtoVpuBxYN6zKKg-BHyZw',4,NULL,NULL,0,0,NULL,'2026-09-23 10:17:52',NULL),(69,4,'Supper.png','cb1b086533db4b46b03a583f84924ae2_Supper.png',507179,'image/png','ByaVTYrCOJuAsytUn8xyqQbM2vOFXqbPwRiUufulA0M',4,NULL,NULL,0,0,NULL,'2026-09-23 10:17:52',NULL),(70,4,'Video.png','c3086e0f6d7a4ae98c6e51d20b5570fc_Video.png',587,'image/png','gI9tsYvwND3oG1HCdeS2qRCBKK4eH6kHwJRQjBBDukQ',4,NULL,NULL,0,0,NULL,'2026-09-23 10:17:52',NULL),(71,4,'Water.png','9b0299cfe5aa4a6084a0eab066dbc879_Water.png',542501,'image/png','70nA1diHnKkXWOBuiLKWdNyrZKUOu-EqctfBNiFMx7k',4,NULL,NULL,0,0,NULL,'2026-09-23 10:17:53',NULL),(72,4,'Word.png','4acc94091e17409bbc07cf45eebc7c79_Word.png',680,'image/png','qxY4bm-g8JuraoqGwZQUb_LoOVRPIifwOfJ3Q_Rqog8',4,NULL,NULL,0,0,NULL,'2026-09-23 10:17:53',NULL),(73,4,'Zip.png','f27e61f197004daeb5868abd5472c8d7_Zip.png',828,'image/png','gwm72sfzk2NjVug_oMlZ9-f6ws0_pUqkXvWmeHDeDek',4,NULL,NULL,0,0,NULL,'2026-09-23 10:17:54',NULL),(74,4,'Group_90.png','2e5fb5ae106249e6971bc67aa296f271_Group_90.png',7351449,'image/png','y-PA2oZQX-d-ZUbTNthmmABu67WV5ocvc6kPAikb0B0',NULL,1,NULL,0,0,NULL,'2026-09-23 10:36:45',NULL),(75,4,'Joshua_Duenas_-_Resume.pdf','3e086a5bad9d44db939ed29db79404ae_Joshua_Duenas_-_Resume.pdf',106109,'application/pdf','CfB8YSVYacnYIf120AXpDavtAlSfeu_u8KHnI1y8w0A',NULL,1,NULL,0,0,NULL,'2026-09-23 10:50:22',NULL);
/*!40000 ALTER TABLE `files` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `folders`
--

DROP TABLE IF EXISTS `folders`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `folders` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `user_id` int unsigned NOT NULL,
  `parent_id` int unsigned DEFAULT NULL,
  `event_id` int unsigned DEFAULT NULL,
  `original_parent_id` int unsigned DEFAULT NULL,
  `name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `share_token` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_starred` tinyint(1) NOT NULL DEFAULT '0',
  `is_deleted` tinyint(1) NOT NULL DEFAULT '0',
  `deleted_at` timestamp NULL DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `accessed_at` timestamp NULL DEFAULT NULL,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_folders_share_token` (`share_token`),
  KEY `idx_folders_user_parent` (`user_id`,`parent_id`,`is_deleted`),
  KEY `fk_folders_parent` (`parent_id`),
  CONSTRAINT `fk_folders_parent` FOREIGN KEY (`parent_id`) REFERENCES `folders` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_folders_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `folders`
--

LOCK TABLES `folders` WRITE;
/*!40000 ALTER TABLE `folders` DISABLE KEYS */;
INSERT INTO `folders` VALUES (1,4,NULL,NULL,NULL,'Testtt','56820ddb9e2e11f1bf5940c2ba07daba',1,0,NULL,'2026-08-19 09:06:29','2026-09-23 05:46:56','2026-09-23 05:46:56'),(3,4,NULL,NULL,NULL,'My_2nd_Folder','56821b109e2e11f1bf5940c2ba07daba',0,0,NULL,'2026-08-20 10:17:59','2026-09-23 09:53:13','2026-09-23 09:53:13'),(4,4,NULL,NULL,NULL,'images','56821d219e2e11f1bf5940c2ba07daba',0,0,NULL,'2026-08-20 10:45:20','2026-09-23 22:28:27','2026-09-23 22:28:27'),(5,4,3,NULL,NULL,'Folder_inside_a_folder','56821e239e2e11f1bf5940c2ba07daba',0,0,NULL,'2026-08-21 06:32:37','2026-08-21 08:59:24','2026-08-26 06:57:37');
/*!40000 ALTER TABLE `folders` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `system_settings`
--

DROP TABLE IF EXISTS `system_settings`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `system_settings` (
  `setting_key` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `setting_value` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`setting_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `system_settings`
--

LOCK TABLES `system_settings` WRITE;
/*!40000 ALTER TABLE `system_settings` DISABLE KEYS */;
/*!40000 ALTER TABLE `system_settings` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `user_preferences`
--

DROP TABLE IF EXISTS `user_preferences`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_preferences` (
  `user_id` int unsigned NOT NULL,
  `display_name` varchar(80) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `theme_preference` varchar(10) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'light',
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`user_id`),
  CONSTRAINT `fk_user_preferences_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `user_preferences`
--

LOCK TABLES `user_preferences` WRITE;
/*!40000 ALTER TABLE `user_preferences` DISABLE KEYS */;
INSERT INTO `user_preferences` VALUES (4,'','light','2026-09-23 22:05:34');
/*!40000 ALTER TABLE `user_preferences` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `users` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `email` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `username` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `password_hash` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `role` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT 'admin',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `is_active` tinyint(1) NOT NULL DEFAULT '1',
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`),
  UNIQUE KEY `uq_users_username` (`username`),
  UNIQUE KEY `email` (`email`),
  UNIQUE KEY `uq_users_email` (`email`),
  KEY `idx_users_created_at` (`created_at`),
  CONSTRAINT `chk_users_role` CHECK (((`role` is null) or (`role` in (_utf8mb4'admin',_utf8mb4'super-admin'))))
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `users`
--

LOCK TABLES `users` WRITE;
/*!40000 ALTER TABLE `users` DISABLE KEYS */;
INSERT INTO `users` VALUES (4,'joshuaduenas.work@gmail.com','Joe','scrypt:32768:8:1$136BeE2rrIzer6To$b32d783a145c6df013e1e4f7de512431c9db770b9a91a8a87191746a5b96d1c2ae5e8e110898ac5aa2ae44d31689c7fad24dedb2ea96f0851fd4588c5cfbd76b','admin','2026-08-19 04:52:47','2026-08-19 04:56:01',1),(5,NULL,'Harrycillian','scrypt:32768:8:1$JVs64xFakb0Zq0zZ$2297500b0c5e7f78f93461618d6a9dd9a6244b06dbc094338ef6da132abef19e851fcd98f4b3c0ad65af2d33376f862c62e9c824ced76954a4e0a500759c5864','super-admin','2026-09-24 12:48:44','2026-09-24 12:48:44',1);
/*!40000 ALTER TABLE `users` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-09-25 22:50:52
