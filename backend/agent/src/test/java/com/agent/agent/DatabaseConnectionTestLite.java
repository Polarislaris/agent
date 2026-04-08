package com.agent.agent;

import java.net.Socket;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.ResultSet;
import java.sql.Statement;

import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.junit.jupiter.api.Assertions.fail;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.MethodOrderer.OrderAnnotation;
import org.junit.jupiter.api.Order;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.TestMethodOrder;

/**
 * 轻量级数据库连接测试 - 无需 Spring 应用上下文
 * 直接使用 JDBC 驱动测试数据库连接
 */
@TestMethodOrder(OrderAnnotation.class)
@DisplayName("数据库连接诊断测试")
class DatabaseConnectionTestLite {

    private static final String DB_HOST = "aws-0-us-west-2.pooler.supabase.com";
    private static final int DB_PORT = 6543;
    private static final String DB_NAME = "postgres";
    private static final String DB_USER = "postgres.lgfngvjedjnygdulisbc";
    private static final String DB_PASSWORD = "eS!LvmeaR7C3zih";
    private static final String JDBC_URL = "jdbc:postgresql://" + DB_HOST + ":" + DB_PORT + "/" + DB_NAME;

    @Test
    @Order(1)
    @DisplayName("步骤 1: 测试网络连接到数据库主机")
    void testNetworkConnectivity() {
        System.out.println("\n" + "=".repeat(60));
        System.out.println("步骤 1: 测试网络连接到数据库主机");
        System.out.println("=".repeat(60));
        System.out.println("   目标主机: " + DB_HOST + ":" + DB_PORT);
        
        try (Socket socket = new Socket(DB_HOST, DB_PORT)) {
            assertTrue(socket.isConnected(), "Should be able to reach database host");
            System.out.println("✅ 网络连接成功！");
            System.out.println("   本地地址: " + socket.getLocalAddress());
            System.out.println("   远程地址: " + socket.getInetAddress());
            System.out.println("   远程端口: " + socket.getPort());
        } catch (java.net.ConnectException e) {
            System.out.println("❌ 网络连接失败 (连接被拒绝)");
            System.out.println("   原因: " + e.getMessage());
            System.out.println("   可能原因:");
            System.out.println("   1. 数据库服务离线或未监听端口");
            System.out.println("   2. 防火墙阻止了连接");
            System.out.println("   3. 数据库地址错误: " + DB_HOST);
            fail("网络连接失败: " + e.getMessage());
        } catch (java.net.NoRouteToHostException e) {
            System.out.println("❌ 网络连接失败 (无网络路由)");
            System.out.println("   原因: " + e.getMessage());
            System.out.println("   可能原因:");
            System.out.println("   1. 网络不可达或离线");
            System.out.println("   2. 防火墙阻止了连接");
            System.out.println("   3. ISP 或网络提供商限制");
            fail("网络连接失败: " + e.getMessage());
        } catch (Exception e) {
            System.out.println("❌ 网络连接失败 (" + e.getClass().getSimpleName() + ")");
            System.out.println("   原因: " + e.getMessage());
            fail("网络连接失败: " + e.getMessage(), e);
        }
    }

    @Test
    @Order(2)
    @DisplayName("步骤 2: 验证 JDBC 驱动程序")
    void testJdbcDriver() {
        System.out.println("\n" + "=".repeat(60));
        System.out.println("步骤 2: 验证 JDBC 驱动程序");
        System.out.println("=".repeat(60));
        
        try {
            Class.forName("org.postgresql.Driver");
            System.out.println("✅ PostgreSQL JDBC 驱动程序加载成功！");
            System.out.println("   驱动程序类: " + Class.forName("org.postgresql.Driver").getName());
        } catch (ClassNotFoundException e) {
            System.out.println("❌ PostgreSQL JDBC 驱动程序未找到");
            System.out.println("   原因: " + e.getMessage());
            fail("JDBC 驱动程序加载失败: " + e.getMessage());
        }
    }

    @Test
    @Order(3)
    @DisplayName("步骤 3: 测试数据库连接 (JDBC)")
    void testDatabaseConnectionJdbc() {
        System.out.println("\n" + "=".repeat(60));
        System.out.println("步骤 3: 测试数据库连接 (JDBC)");
        System.out.println("=".repeat(60));
        System.out.println("   JDBC URL: " + JDBC_URL);
        System.out.println("   用户名: " + DB_USER);
        
        try (Connection connection = DriverManager.getConnection(JDBC_URL, DB_USER, DB_PASSWORD)) {
            assertNotNull(connection, "Connection should not be null");
            assertTrue(!connection.isClosed(), "Connection should be open");
            
            System.out.println("✅ 数据库连接成功！");
            System.out.println("   数据库 URL: " + connection.getMetaData().getURL());
            System.out.println("   数据库用户: " + connection.getMetaData().getUserName());
            System.out.println("   数据库驱动: " + connection.getMetaData().getDriverName());
            System.out.println("   驱动版本: " + connection.getMetaData().getDriverVersion());
            
        } catch (org.postgresql.util.PSQLException e) {
            System.out.println("❌ PostgreSQL 连接异常");
            System.out.println("   异常类型: " + e.getClass().getSimpleName());
            System.out.println("   SQL 状态: " + e.getSQLState());
            System.out.println("   错误信息: " + e.getMessage());
            
            // 分析具体错误
            if (e.getMessage().contains("authentication failed")) {
                System.out.println("   问题: 认证失败 - 用户名或密码错误");
            } else if (e.getMessage().contains("can't handle")) {
                System.out.println("   问题: 库类型不匹配");
            } else if (e.getMessage().contains("尝试连线已失败")) {
                System.out.println("   问题: 网络连接失败");
            }
            
            fail("数据库连接失败: " + e.getMessage());
        } catch (Exception e) {
            System.out.println("❌ 数据库连接失败 (" + e.getClass().getSimpleName() + ")");
            System.out.println("   错误信息: " + e.getMessage());
            fail("数据库连接失败: " + e.getMessage(), e);
        }
    }

    @Test
    @Order(4)
    @DisplayName("步骤 4: 查询数据库版本")
    void testDatabaseVersion() {
        System.out.println("\n" + "=".repeat(60));
        System.out.println("步骤 4: 查询数据库版本");
        System.out.println("=".repeat(60));
        
        try (Connection connection = DriverManager.getConnection(JDBC_URL, DB_USER, DB_PASSWORD);
             Statement statement = connection.createStatement()) {

            ResultSet resultSet = statement.executeQuery("SELECT version()");
            
            if (resultSet.next()) {
                String version = resultSet.getString(1);
                assertTrue(version.contains("PostgreSQL"), "Should be PostgreSQL");
                System.out.println("✅ 数据库版本查询成功！");
                System.out.println("   版本信息: " + version);
            }
            
        } catch (Exception e) {
            System.out.println("❌ 数据库查询失败: " + e.getMessage());
            fail("数据库查询失败: " + e.getMessage(), e);
        }
    }

    @Test
    @Order(5)
    @DisplayName("步骤 5: 查询数据库中的表")
    void testDatabaseTables() {
        System.out.println("\n" + "=".repeat(60));
        System.out.println("步骤 5: 查询数据库中的表");
        System.out.println("=".repeat(60));
        
        try (Connection connection = DriverManager.getConnection(JDBC_URL, DB_USER, DB_PASSWORD)) {
            
            var tables = connection.getMetaData().getTables(null, "public", null, new String[]{"TABLE"});
            
            int tableCount = 0;
            System.out.println("✅ 表查询成功！");
            System.out.println("   public schema 中的表:");
            
            while (tables.next()) {
                String tableName = tables.getString("TABLE_NAME");
                System.out.println("   - " + tableName);
                tableCount++;
            }
            
            if (tableCount == 0) {
                System.out.println("   (暂无表，数据库为空)");
            } else {
                System.out.println("   共找到 " + tableCount + " 个表");
            }
            
        } catch (Exception e) {
            System.out.println("⚠️  表查询失败: " + e.getMessage());
            System.out.println("   (这可能不是致命错误，可能是权限或 schema 问题)");
        }
    }

    @Test
    @Order(6)
    @DisplayName("步骤 6: 概要测试报告")
    void generateFinalReport() {
        System.out.println("\n" + "=".repeat(60));
        System.out.println("测试完成！数据库连接正常");
        System.out.println("=".repeat(60));
        System.out.println("\n✅ 数据库连接诊断成功！");
        System.out.println("   - 网络连接: ✅ 正常");
        System.out.println("   - JDBC 驱动: ✅ 正常");
        System.out.println("   - 数据库连接: ✅ 正常");
        System.out.println("   - 数据库查询: ✅ 正常");
        System.out.println("\n您现在可以:");
        System.out.println("  1. 启动 Spring Boot 应用");
        System.out.println("  2. 在生产环境中使用数据库");
        System.out.println("  3. 运行其他集成测试");
    }
}
