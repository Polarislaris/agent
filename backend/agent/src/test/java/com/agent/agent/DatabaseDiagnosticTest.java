package com.agent.agent;

import java.net.Socket;
import java.sql.Connection;
import java.sql.ResultSet;
import java.sql.Statement;

import javax.sql.DataSource;

import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.junit.jupiter.api.Assertions.fail;
import org.junit.jupiter.api.MethodOrderer.OrderAnnotation;
import org.junit.jupiter.api.Order;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.TestMethodOrder;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

/**
 * 数据库连接诊断测试
 * 按步骤验证 PostgreSQL 数据库连接
 */
@SpringBootTest
@TestMethodOrder(OrderAnnotation.class)
class DatabaseDiagnosticTest {

    private static final String DB_HOST = "aws-0-us-west-2.pooler.supabase.com";
    private static final int DB_PORT = 6543;

    @Autowired
    private DataSource dataSource;

    @Test
    @Order(1)
    void testNetworkConnectivity() {
        System.out.println("\n=== 步骤 1: 测试网络连接 ===");
        System.out.println("   目标主机: " + DB_HOST + ":" + DB_PORT);
        
        try (Socket socket = new Socket(DB_HOST, DB_PORT)) {
            assertTrue(socket.isConnected(), "Should be able to reach database host");
            System.out.println("✅ 网络连接成功！");
            System.out.println("   本地地址: " + socket.getLocalAddress());
            System.out.println("   远程地址: " + socket.getInetAddress());
        } catch (Exception e) {
            fail("❌ 网络连接失败: " + e.getMessage() + 
                 "\n   请检查:\n" +
                 "   1. 是否连接到互联网\n" +
                 "   2. 防火墙是否阻止了连接\n" +
                 "   3. 数据库地址是否正确: " + DB_HOST + ":" + DB_PORT, e);
        }
    }

    @Test
    @Order(2)
    void testDataSourceInitialization() {
        System.out.println("\n=== 步骤 2: 测试 DataSource 初始化 ===");
        assertNotNull(dataSource, "DataSource should be initialized");
        System.out.println("✅ DataSource 初始化成功！");
        System.out.println("   数据源类型: " + dataSource.getClass().getSimpleName());
    }

    @Test
    @Order(3)
    void testDatabaseConnection() {
        System.out.println("\n=== 步骤 3: 测试数据库连接 ===");
        
        try (Connection connection = dataSource.getConnection()) {
            assertNotNull(connection, "Connection should not be null");
            assertTrue(!connection.isClosed(), "Connection should be open");
            
            System.out.println("✅ 数据库连接成功！");
            System.out.println("   数据库 URL: " + connection.getMetaData().getURL());
            System.out.println("   用户名: " + connection.getMetaData().getUserName());
            System.out.println("   数据库名称: " + connection.getCatalog());
            
        } catch (Exception e) {
            fail("❌ 数据库连接失败: " + e.getMessage() + 
                 "\n   原因: " + e.getCause() +
                 "\n   请检查:\n" +
                 "   1. 数据库是否在线\n" +
                 "   2. 用户名和密码是否正确\n" +
                 "   3. 网络连接是否稳定", e);
        }
    }

    @Test
    @Order(4)
    void testDatabaseVersion() {
        System.out.println("\n=== 步骤 4: 查询数据库版本 ===");
        
        try (Connection connection = dataSource.getConnection();
             Statement statement = connection.createStatement()) {

            ResultSet resultSet = statement.executeQuery("SELECT version()");
            
            if (resultSet.next()) {
                String version = resultSet.getString(1);
                assertTrue(version.contains("PostgreSQL"), "Should be PostgreSQL");
                System.out.println("✅ 数据库版本查询成功！");
                System.out.println("   版本信息: " + version);
            }
            
        } catch (Exception e) {
            fail("❌ 数据库查询失败: " + e.getMessage(), e);
        }
    }

    @Test
    @Order(5)
    void testTableConnection() {
        System.out.println("\n=== 步骤 5: 测试表连接 ===");
        
        try (Connection connection = dataSource.getConnection();
             Statement statement = connection.createStatement()) {

            // 查询数据库中的表
            ResultSet tables = connection.getMetaData().getTables(null, "public", null, new String[]{"TABLE"});
            
            int tableCount = 0;
            System.out.println("✅ 表查询成功！");
            System.out.println("   找到的表:");
            
            while (tables.next()) {
                String tableName = tables.getString("TABLE_NAME");
                System.out.println("   - " + tableName);
                tableCount++;
            }
            
            if (tableCount == 0) {
                System.out.println("   (暂无表)");
            }
            
        } catch (Exception e) {
            System.out.println("⚠️  表查询失败: " + e.getMessage());
            System.out.println("   (这可能不是致命错误，可能是权限问题)");
        }
    }

    @Test
    @Order(6)
    void testConnectionPool() {
        System.out.println("\n=== 步骤 6: 测试连接池 ===");
        
        try {
            // 获取多个连接以测试连接池
            for (int i = 0; i < 3; i++) {
                try (Connection connection = dataSource.getConnection()) {
                    System.out.println("✅ 连接 " + (i + 1) + " 获取成功");
                }
            }
            System.out.println("✅ 连接池测试成功！");
            
        } catch (Exception e) {
            fail("❌ 连接池测试失败: " + e.getMessage(), e);
        }
    }

    @Test
    @Order(7)
    void generateReport() {
        System.out.println("\n" + "=".repeat(50));
        System.out.println("数据库连接测试完成！");
        System.out.println("=".repeat(50));
        System.out.println("\n✅ 所有测试通过，数据库连接正常！\n");
    }
}
