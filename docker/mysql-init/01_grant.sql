-- analyst 账号需要建库 / 删库权限：流程会重建 qc_dw（数仓）和 qc_interview（SQL 面试库）
GRANT ALL PRIVILEGES ON *.* TO 'analyst'@'%';
FLUSH PRIVILEGES;
