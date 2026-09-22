-- phpMyAdmin SQL Dump
-- version 5.2.0
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Generation Time: Aug 26, 2026 at 07:25 AM
-- Server version: 10.4.24-MariaDB
-- PHP Version: 8.1.6

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `jf_pila`
--

-- --------------------------------------------------------

--
-- Table structure for table `events`
--

CREATE TABLE `events` (
  `id` int(10) UNSIGNED NOT NULL,
  `user_id` int(10) UNSIGNED NOT NULL,
  `name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `event_date` date NOT NULL,
  `event_type` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'event',
  `is_starred` tinyint(1) NOT NULL DEFAULT 0,
  `is_deleted` tinyint(1) NOT NULL DEFAULT 0,
  `deleted_at` timestamp NULL DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `share_token` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `events`
--

INSERT INTO `events` (`id`, `user_id`, `name`, `event_date`, `event_type`, `is_starred`, `is_deleted`, `deleted_at`, `created_at`, `updated_at`, `share_token`) VALUES
(1, 4, 'Youth_KAPEllowship', '2026-08-15', 'fellowship', 0, 0, NULL, '2026-08-25 12:38:38', '2026-08-26 06:57:37', '5682206c9e2e11f1bf5940c2ba07daba');

--
-- Table structure for table `files`
--

CREATE TABLE `files` (
  `id` int(10) UNSIGNED NOT NULL,
  `user_id` int(10) UNSIGNED NOT NULL,
  `original_filename` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `stored_filename` varchar(320) COLLATE utf8mb4_unicode_ci NOT NULL,
  `file_size` bigint(20) UNSIGNED NOT NULL,
  `mime_type` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `share_token` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `folder_id` int(10) UNSIGNED DEFAULT NULL,
  `event_id` int(10) UNSIGNED DEFAULT NULL,
  `original_folder_id` int(10) UNSIGNED DEFAULT NULL,
  `is_starred` tinyint(1) NOT NULL DEFAULT 0,
  `is_deleted` tinyint(1) NOT NULL DEFAULT 0,
  `deleted_at` timestamp NULL DEFAULT NULL,
  `uploaded_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `accessed_at` timestamp NULL DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `files`
--

INSERT INTO `files` (`id`, `user_id`, `original_filename`, `stored_filename`, `file_size`, `mime_type`, `share_token`, `folder_id`, `event_id`, `original_folder_id`, `is_starred`, `is_deleted`, `deleted_at`, `uploaded_at`, `accessed_at`) VALUES
(1, 4, 'Untitled_design.png', '0c4254ca296448329a053974a9a8eee8_Untitled_design.png', 869703, 'image/png', 'DSgTtLOERFloEk6FwvXaBCLwwu_p6SzWL349t-iL4dc', NULL, NULL, NULL, 0, 0, NULL, '2026-08-19 08:50:48', '2026-08-26 07:21:05'),
(2, 4, '79eafa7bbd24e733a206a071e87adb32.jpg', '5008837248a94de1bd04a85958fe47d4_79eafa7bbd24e733a206a071e87adb32.jpg', 58051, 'image/jpeg', 'U-HUnhky5UY0Tgi3q0F7fk76AYkB6dttWlAJxQlSmSw', NULL, NULL, NULL, 0, 0, NULL, '2026-08-19 08:50:48', '2026-08-26 05:37:23'),
(3, 4, 'Week02_CMSC305_Seatwork2.docx', '50b8658879c54e6fa3907438405e073b_Week02_CMSC305_Seatwork2.docx', 485281, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'uXAdr5XFZZ4DgLxh764MF_D4A-HuOxq98yjS3Tqkngk', NULL, NULL, NULL, 0, 0, NULL, '2026-08-19 08:50:48', '2026-08-26 05:37:29'),
(4, 4, 'Week03_CMSC306_Lab_Experiment_02_Subtractor_Circuit.docx', '6fd772c1024e41c28713784db6321c80_Week03_CMSC306_Lab_Experiment_02_Subtractor_Circuit.docx', 499548, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'D3N55I5oYNKt_hoWu3SbQfaLDOhyzoRoiCU7zwLz8Yw', NULL, NULL, NULL, 0, 0, NULL, '2026-08-19 08:50:48', NULL),
(5, 4, 'Joshua_Duenas_-_Resume.pdf', 'f47e3ab9355a4c81a06df2c21b77f0c0_Joshua_Duenas_-_Resume.pdf', 106374, 'application/pdf', 'lrkdLg_ZixdUYklSVn9F9B4BeZDrHwffj1iXCDwD650', NULL, NULL, NULL, 0, 0, NULL, '2026-08-19 08:50:48', NULL),
(6, 4, 'tinytask.ini', '077f2953b2504d369af8e3189b2b6570_tinytask.ini', 138, 'application/octet-stream', 'gQma_bHjjs8ccHQxGAaAOURv-LqFPZk80Jzk3kTnZlw', 1, NULL, NULL, 0, 0, NULL, '2026-08-19 10:04:52', NULL),
(7, 4, '57-579715_snoopy-sleeping-png-snoopy-sleeping-clip-art-snoopy.png', 'b3e01470109c4d55bf5a3e61e682b634_57-579715_snoopy-sleeping-png-snoopy-sleeping-clip-art-snoopy.png', 626833, 'image/png', 'f0i27kWBlQ4AJVPXmtYjZaFSY_P4LKzKNDG4V7my_GY', NULL, NULL, NULL, 0, 0, NULL, '2026-08-19 10:04:52', NULL),
(8, 4, 'FINAL-REQUIREMENTS-CHECKLIST-2025.pdf', '6689ebb53bc24c49860fb8eda25c9a3a_FINAL-REQUIREMENTS-CHECKLIST-2025.pdf', 81428, 'application/pdf', '-1TFE2hGtMCVllS3HajsjoRLdv6oTS0QECphIP2TQkM', NULL, NULL, NULL, 0, 0, NULL, '2026-08-19 10:04:52', NULL),
(10, 4, 'A_Comparative_Analysis_of_the_Problems_Experienced_by_Senior_High_School_Students_of_San_Antonio_de_Padua_College_Foundation_Pila_Laguna_School_Years_20242025_and_20252026__Basis_for_an_Intervention_Program_1.pdf', '38819f72478a4ec8b99ff0e5ca7b2be5_A_Comparative_Analysis_of_the_Problems_Experienced_by_Senior_High_School_Students_of_San_Antonio_de_Padua_College_Foundation_Pila_Laguna_School_Years_20242025_and_20252026__Basis_for_an_Intervention_Program_1.pdf', 2115635, 'application/pdf', '_KKNePBtvz0ABBm8NS5hD7KJdz0l4Ygul0AbNg2hkMI', NULL, NULL, NULL, 1, 0, NULL, '2026-08-19 10:04:52', '2026-08-21 10:36:03'),
(11, 4, 'JF_Pila_-_Youth.xlsx', '4932497c59954c76806a4d031f0417db_JF_Pila_-_Youth.xlsx', 301824, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', '0uUfK0-uCZuDRQXGPSd7k-JLEU7jmem0gg3oGXF3fJo', NULL, NULL, NULL, 0, 0, NULL, '2026-08-20 05:17:05', NULL),
(12, 4, 'tinytask.ini', 'b4c1bc0bc4ab4fcca25e5fa010f8d8f7_tinytask.ini', 138, 'application/octet-stream', 'j5o21UyAqadF39KLXiVi8hRw9AgEXfNIIOspkLFDlUQ', NULL, NULL, NULL, 0, 1, '2026-08-20 05:17:49', '2026-08-20 05:17:21', NULL),
(13, 4, 'app.js', 'ed788a7177914c4282364a6f65f8ed35_app.js', 38147, 'text/javascript', 'Za8RTsXWo9C2WOjynCUVsFCdS38pMU1x9sk1JI2NqZc', NULL, NULL, NULL, 0, 0, NULL, '2026-08-20 10:43:03', '2026-08-22 15:04:58'),
(14, 4, 'Audio.png', 'd91d7e5254a44d568a46bdc0044db9b0_Audio.png', 682, 'image/png', '56hSnqg1LqW31h_FsMO_0LV-nRbqKZGHuO-kMEucYJg', 4, NULL, NULL, 0, 0, NULL, '2026-08-20 10:45:20', NULL),
(15, 4, 'CLOSE.png', '617d0a4d0baf4ab9b9bcf900ce959f8d_CLOSE.png', 1065, 'image/png', 'tiTjzWDaFQZ2yAj7rAvIOYCdqlN5IN7HdhvCRDLraow', 4, NULL, NULL, 0, 0, NULL, '2026-08-20 10:45:20', NULL),
(16, 4, 'CLOSE_hover.png', 'b92259051772430ebad3a6c1fefa3b05_CLOSE_hover.png', 1059, 'image/png', 'pVgdxfYXVKzPNfVd7A2f7uOTi_JxIWUH0RwkoD55jkQ', 4, NULL, NULL, 0, 0, NULL, '2026-08-20 10:45:20', NULL),
(17, 4, 'CPL.png', '3c2ed86b4ddb48a691a2395dea9ab734_CPL.png', 2340, 'image/png', 'JjqPY-NRTiqa7KD9oMv4MR7tOw9skY6MMhOJutb3690', 4, NULL, NULL, 0, 0, NULL, '2026-08-20 10:45:20', NULL),
(18, 4, 'CPL_hover.png', '1715556147414563801d889c47724f51_CPL_hover.png', 2818, 'image/png', 'AhmapnWb_B36OfBC1uGXjz98OCCKHyhwIt0fvPwgSo8', 4, NULL, NULL, 0, 0, NULL, '2026-08-20 10:45:20', NULL),
(19, 4, 'DEL.png', 'd7080423da8442b5a25852f5e7f1f5a0_DEL.png', 1917, 'image/png', 'CY6hQfJG-kBQ4tbTXuFNMy8jKeNPJa1zi1C7WjZVYU8', 4, NULL, NULL, 0, 0, NULL, '2026-08-20 10:45:20', NULL),
(20, 4, 'DEL_hover.png', 'c7db4e1092164464908ca56e267d3fd7_DEL_hover.png', 1924, 'image/png', 'vXiWDhyhrDvc8VTya0J1eeERtvX50QVlpWTKMpuklrg', 4, NULL, NULL, 0, 0, NULL, '2026-08-20 10:45:20', NULL),
(21, 4, 'DL.png', '76d2d3d41ecd4a7cb8379ff982714fdc_DL.png', 2500, 'image/png', 'HOXb__trVIzQfVsW_UtqY9KFP9AuVzmtC__Srw8K-aU', 4, NULL, NULL, 0, 0, NULL, '2026-08-20 10:45:20', NULL),
(22, 4, 'DLfile.png', '8c7df437b94341938d73eddcb42b90f8_DLfile.png', 2791, 'image/png', 'RQb3ACM8jGN_8npuVDG-pwr9eMaaZj4vcXlwG2XthR4', 4, NULL, NULL, 0, 0, NULL, '2026-08-20 10:45:20', NULL),
(23, 4, 'DLfile_hover.png', 'fbf2cc01459b453a903189f03280274c_DLfile_hover.png', 2814, 'image/png', 'NjXzp8oUj2tz2a7eyr66oGeU7cHsjRvwAqo64h5o14s', 4, NULL, NULL, 0, 0, NULL, '2026-08-20 10:45:20', NULL),
(24, 4, 'DL_hover.png', 'a66480db976e431c99e069bab66cca7b_DL_hover.png', 2466, 'image/png', 'wmtxNZl3ayeD55fH_6U360HSpWTOR7HDn5TTDxIRg1g', 4, NULL, NULL, 0, 0, NULL, '2026-08-20 10:45:20', NULL),
(25, 4, 'File.png', '25ffa512bbfd4aecbf6b5b13555ccf2f_File.png', 560, 'image/png', 'Skcc04Au8IDUzcPrawihO820IR0_Wvd5LDJcpHamXKs', 4, NULL, NULL, 0, 0, NULL, '2026-08-20 10:45:20', NULL),
(26, 4, 'FL.png', '190909ec4aa64f7084eac10fd44e8527_FL.png', 1707, 'image/png', 'V3N7RqHC0FOHTbyo6UgOCYOuCkiHWG_qZuU8YRmDH6w', 4, NULL, NULL, 0, 0, NULL, '2026-08-20 10:45:20', NULL),
(27, 4, 'FL_hover.png', '69d9196822364c9383b55a0545908585_FL_hover.png', 1707, 'image/png', 'ohd53__6RiyMGKqHl_m3cB35zOk22eTyT4t0y58dnIg', 4, NULL, NULL, 0, 0, NULL, '2026-08-20 10:45:20', NULL),
(28, 4, 'Folder.png', '3834f0635fd84291b61ad549fd0f7126_Folder.png', 426, 'image/png', 'QpBvmApwu4kkLfSMQI2yoDJY1aaG5UMIatP4B94RVHQ', 4, NULL, NULL, 0, 0, NULL, '2026-08-20 10:45:20', NULL),
(29, 4, 'Image.png', '3efcd7a1a45e40c5b0c3fec439718023_Image.png', 542, 'image/png', '7POLZQDu7N0d0-BpMJM_WpuHeoHIGBImcBE9YMAREVY', 4, NULL, NULL, 0, 0, NULL, '2026-08-20 10:45:20', NULL),
(30, 4, 'JF.ico', '96dd2cb5e6d2481c920db132615559ab_JF.ico', 4022, 'image/x-icon', 'JL4qQCzhmbIc0BTz1CxiC11gX9Frcjq0jW6Nu_2dxGY', 4, NULL, NULL, 0, 0, NULL, '2026-08-20 10:45:20', NULL),
(31, 4, 'JF.png', '858efcb719194c2cb4a7f81ab77e73d8_JF.png', 26404, 'image/png', 'PUBeXFUy-0DF60xUiMIsAl5S-mklmIX9xbID0imziBs', 4, NULL, NULL, 0, 0, NULL, '2026-08-20 10:45:20', NULL),
(32, 4, 'jfcm.png', '967745206a844e5885feb2470a20c746_jfcm.png', 81616, 'image/png', '89PFVEoVK2Yl7RGmPYEcOFPpXzUnzxZVVz17_KXX4bw', 4, NULL, NULL, 0, 0, NULL, '2026-08-20 10:45:20', NULL),
(33, 4, 'mingcute_pdf-fill.png', 'df7bbe7321be438e8937fe691f2baec7_mingcute_pdf-fill.png', 688, 'image/png', 'k5Gx8oIaiGQFyyNFqnxcEbGpSHoU8F9J-EXTNQFBQyw', 4, NULL, NULL, 0, 0, NULL, '2026-08-20 10:45:20', NULL),
(34, 4, 'PDF.png', 'fc223bdd4254485094575676010631c9_PDF.png', 1042, 'image/png', 'brTnOxByu--UG84Oe0M41lnJnggbuw1runXICEjXijc', 4, NULL, NULL, 0, 0, NULL, '2026-08-20 10:45:20', NULL),
(35, 4, 'PPT.png', '0fcabe3b149f49aeaeb8d5efc5bbde20_PPT.png', 758, 'image/png', 'Yd-XCVBDATDAFxZQB7iJCaiznJ0FshebbvpUj6bv4hc', 4, NULL, NULL, 0, 0, NULL, '2026-08-20 10:45:20', NULL),
(36, 4, 'reicon_audio-square-filled.png', '95af24fae592433abb226bec037be218_reicon_audio-square-filled.png', 917, 'image/png', 'uFrsPISbt6spwrttZE6Z7xhGiEjBPHVCHxD4YTdrsr4', 4, NULL, NULL, 0, 0, NULL, '2026-08-20 10:45:20', NULL),
(37, 4, 'reicon_doc-text-filled.png', 'ccbdcb9967d04003a9b4347002c152de_reicon_doc-text-filled.png', 680, 'image/png', 'x8_DH4f4LIfmYNddtLwqQohZj3GsYPEDWmxMap5eCN4', 4, NULL, NULL, 0, 0, NULL, '2026-08-20 10:45:20', NULL),
(38, 4, 'RN.png', 'f9a2c68f88c3454fab92d3f605e2ef41_RN.png', 2312, 'image/png', 'yfu7lUl5koV1n5lOAYxt5AISd-_Hao0XOL9gBEYTWQ8', 4, NULL, NULL, 0, 0, NULL, '2026-08-20 10:45:20', NULL),
(39, 4, 'RN_hover.png', '48fe36e57d8844d1b0c73f70b7c5b309_RN_hover.png', 2392, 'image/png', 'eqqnjcHvFOxoKJHtDwl709TG2gjMujULV_dNFeZzf9E', 4, NULL, NULL, 0, 0, NULL, '2026-08-20 10:45:20', NULL),
(40, 4, 'solar_file-bold.png', '60190392c2ae4fa0835af4b9ffd27546_solar_file-bold.png', 742, 'image/png', '0-QYG9WMlJNgsi0bbRyxu_rUdME7PAuyvTa8ujU31s4', 4, NULL, NULL, 0, 0, NULL, '2026-08-20 10:45:20', NULL),
(41, 4, 'Spreadsheet.png', 'cd67bfebdb264017bb33beb8e55c063e_Spreadsheet.png', 589, 'image/png', 'tnMG3d17qBwoqQi3mr4fVjB2efu9SvSfZlZVB9d3smY', 4, NULL, NULL, 0, 0, NULL, '2026-08-20 10:45:20', NULL),
(42, 4, 'Video.png', '5ce7a8b18c1049e38aab099664dd6c55_Video.png', 587, 'image/png', 'RoXByH1XtwY9jeNlsFDTNVG3G1N8nUegoqrIcdJklWs', 4, NULL, NULL, 0, 0, NULL, '2026-08-20 10:45:20', NULL),
(43, 4, 'VW.png', '7f542f59adea42f487d9944f6bd33855_VW.png', 2141, 'image/png', 'qgTRYqSspPumxbOKXszsXjkTJiI4jXYCUxpK2WNP0qc', 4, NULL, NULL, 0, 0, NULL, '2026-08-20 10:45:20', NULL),
(44, 4, 'VW_hover.png', 'f0e980ff480c48eda6ae65706bca83e2_VW_hover.png', 2665, 'image/png', 'gxapCUuaG7sNznjPaFtMOxHroJdYHancGe_QvneXgi8', 4, NULL, NULL, 0, 0, NULL, '2026-08-20 10:45:20', NULL),
(45, 4, 'Word.png', '29d9047c94b14e84b3227db0610859dd_Word.png', 791, 'image/png', 'BS7cqsB5JFQNEZ-jJgdFfC5-l4dGN14wm2Ei1ojpfoU', 4, NULL, NULL, 0, 0, NULL, '2026-08-20 10:45:20', NULL),
(46, 4, 'frank-ocean-blond-music-rjr51ik7cbd17sgb.jpg', '0a5d6ca3005841828ff515abcb107db3_frank-ocean-blond-music-rjr51ik7cbd17sgb.jpg', 251638, 'image/jpeg', 'eRVo16rgxfmJztGkjCeD2z-cjC_ZBbUdVYqzeB0YbtE', NULL, NULL, NULL, 0, 0, NULL, '2026-08-20 15:59:18', '2026-08-21 10:28:56'),
(47, 4, 'maxresdefault.jpg', 'f3a281a26ae74015a7eccc0f31fb2306_maxresdefault.jpg', 73243, 'image/jpeg', '1t_Vf7KtHmGo2oioDtxkd_zl1gCrhRa83YbMOD39Kcs', 4, NULL, 4, 0, 0, NULL, '2026-08-20 18:49:05', NULL),
(48, 4, 'GELO.mp4', '9ba4ebf419104b36a17bc44e02b2a001_GELO.mp4', 2239947, 'video/mp4', '9ow0l_zGL3udIpjkVuX4SUvRd9H0nlflVOay3XXCqU0', NULL, NULL, NULL, 0, 0, NULL, '2026-08-26 07:13:16', '2026-08-26 07:22:09');

--
-- Table structure for table `folders`
--

CREATE TABLE `folders` (
  `id` int(10) UNSIGNED NOT NULL,
  `user_id` int(10) UNSIGNED NOT NULL,
  `parent_id` int(10) UNSIGNED DEFAULT NULL,
  `event_id` int(10) UNSIGNED DEFAULT NULL,
  `original_parent_id` int(10) UNSIGNED DEFAULT NULL,
  `name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `share_token` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_starred` tinyint(1) NOT NULL DEFAULT 0,
  `is_deleted` tinyint(1) NOT NULL DEFAULT 0,
  `deleted_at` timestamp NULL DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `accessed_at` timestamp NULL DEFAULT NULL,
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `folders`
--

INSERT INTO `folders` (`id`, `user_id`, `parent_id`, `event_id`, `original_parent_id`, `name`, `share_token`, `is_starred`, `is_deleted`, `deleted_at`, `created_at`, `accessed_at`, `updated_at`) VALUES
(1, 4, NULL, NULL, NULL, 'Testtt', '56820ddb9e2e11f1bf5940c2ba07daba', 1, 0, NULL, '2026-08-19 09:06:29', NULL, '2026-08-26 06:57:37'),
(3, 4, NULL, NULL, NULL, 'My_2nd_Folder', '56821b109e2e11f1bf5940c2ba07daba', 0, 0, NULL, '2026-08-20 10:17:59', '2026-08-21 14:00:50', '2026-08-26 06:57:37'),
(4, 4, NULL, NULL, NULL, 'images', '56821d219e2e11f1bf5940c2ba07daba', 0, 0, NULL, '2026-08-20 10:45:20', '2026-08-21 14:19:11', '2026-08-26 06:57:37'),
(5, 4, 3, NULL, NULL, 'Folder_inside_a_folder', '56821e239e2e11f1bf5940c2ba07daba', 0, 0, NULL, '2026-08-21 06:32:37', '2026-08-21 08:59:24', '2026-08-26 06:57:37');

--
-- Table structure for table `users`
--

CREATE TABLE `users` (
  `id` int(10) UNSIGNED NOT NULL,
  `email` varchar(80) COLLATE utf8mb4_unicode_ci NOT NULL,
  `username` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `password_hash` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `users`
--

INSERT INTO `users` (`id`, `email`, `username`, `password_hash`, `created_at`, `updated_at`) VALUES
(4, 'joshuaduenas.work@gmail.com', 'Joe', 'scrypt:32768:8:1$136BeE2rrIzer6To$b32d783a145c6df013e1e4f7de512431c9db770b9a91a8a87191746a5b96d1c2ae5e8e110898ac5aa2ae44d31689c7fad24dedb2ea96f0851fd4588c5cfbd76b', '2026-08-19 04:52:47', '2026-08-19 04:56:01');

--
-- Indexes for dumped tables
--

--
-- Indexes for table `events`
--
ALTER TABLE `events`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `uq_events_share_token` (`share_token`),
  ADD KEY `idx_events_user` (`user_id`,`is_deleted`,`event_date`);

--
-- Indexes for table `files`
--
ALTER TABLE `files`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `uq_files_stored_filename` (`stored_filename`),
  ADD UNIQUE KEY `uq_files_share_token` (`share_token`),
  ADD KEY `idx_files_user_uploaded` (`user_id`,`uploaded_at`),
  ADD KEY `idx_files_user_folder` (`user_id`,`folder_id`,`is_deleted`),
  ADD KEY `fk_files_folder` (`folder_id`),
  ADD KEY `idx_files_user_event` (`user_id`,`event_id`,`is_deleted`),
  ADD KEY `fk_files_event` (`event_id`);

--
-- Indexes for table `folders`
--
ALTER TABLE `folders`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `uq_folders_share_token` (`share_token`),
  ADD KEY `idx_folders_user_parent` (`user_id`,`parent_id`,`is_deleted`),
  ADD KEY `fk_folders_parent` (`parent_id`),
  ADD KEY `idx_folders_user_event` (`user_id`,`event_id`,`is_deleted`),
  ADD KEY `fk_folders_event` (`event_id`);

--
-- Indexes for table `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `username` (`username`),
  ADD UNIQUE KEY `uq_users_username` (`username`),
  ADD KEY `idx_users_created_at` (`created_at`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `events`
--
ALTER TABLE `events`
  MODIFY `id` int(10) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- AUTO_INCREMENT for table `files`
--
ALTER TABLE `files`
  MODIFY `id` int(10) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=49;

--
-- AUTO_INCREMENT for table `folders`
--
ALTER TABLE `folders`
  MODIFY `id` int(10) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=6;

--
-- AUTO_INCREMENT for table `users`
--
ALTER TABLE `users`
  MODIFY `id` int(10) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;

--
-- Constraints for dumped tables
--

--
-- Constraints for table `events`
--
ALTER TABLE `events`
  ADD CONSTRAINT `fk_events_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE;

--
-- Constraints for table `files`
--
ALTER TABLE `files`
  ADD CONSTRAINT `fk_files_event` FOREIGN KEY (`event_id`) REFERENCES `events` (`id`) ON DELETE SET NULL,
  ADD CONSTRAINT `fk_files_folder` FOREIGN KEY (`folder_id`) REFERENCES `folders` (`id`) ON DELETE SET NULL,
  ADD CONSTRAINT `fk_files_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE;

--
-- Constraints for table `folders`
--
ALTER TABLE `folders`
  ADD CONSTRAINT `fk_folders_event` FOREIGN KEY (`event_id`) REFERENCES `events` (`id`) ON DELETE SET NULL,
  ADD CONSTRAINT `fk_folders_parent` FOREIGN KEY (`parent_id`) REFERENCES `folders` (`id`) ON DELETE SET NULL,
  ADD CONSTRAINT `fk_folders_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE;

COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
