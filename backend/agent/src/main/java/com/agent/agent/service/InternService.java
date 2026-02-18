package com.agent.agent.service;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.logging.Logger;

import org.springframework.stereotype.Service;

import com.agent.agent.model.CompanyInfo;
import com.agent.agent.model.InternPost;

@Service
public class InternService {

    private static final Logger LOG = Logger.getLogger(InternService.class.getName());

    private final PythonDataClient pythonClient;

    // In-memory data (populated from Python service or placeholder)
    private final Map<String, InternPost> internPosts = new LinkedHashMap<>();

    public InternService(PythonDataClient pythonClient) {
        this.pythonClient = pythonClient;
        loadData();
    }

    /**
     * 优先从 Python FastAPI 获取数据，失败时 fallback 到本地 placeholder
     */
    private void loadData() {
        List<InternPost> posts = pythonClient.fetchAllInterns();
        if (!posts.isEmpty()) {
            LOG.info("Loaded " + posts.size() + " posts from Python service");
            for (InternPost p : posts) {
                internPosts.put(p.getId(), p);
            }
        } else {
            LOG.info("Python service unavailable, loading placeholder data");
            initPlaceholderData();
        }
    }

    /** 手动刷新数据（可通过新增 endpoint 调用） */
    public void refreshData() {
        internPosts.clear();
        loadData();
    }

    private void initPlaceholderData() {
        addPost("1",  "Full-Stack Intern",     "Dryft",       "San Francisco, CA", "2026-02-09",
                "Join Dryft's engineering team to build and maintain full-stack features using React and Node.js. You will collaborate with senior engineers to design scalable web applications, implement RESTful APIs, and integrate with third-party services. This role involves working across the entire stack — from crafting responsive UIs to optimizing database queries and deploying microservices. Ideal candidates are curious, self-driven, and eager to learn in a fast-paced startup environment.",
                List.of("React", "Node.js", "SQL"), "#",
                new CompanyInfo("50–200 employees", "2021", "Mobility & transportation platform"),
                "★★★★☆  Strong match — Full-Stack aligns well with your React and Node.js skills.",
                "Medium — Competitive but smaller applicant pool compared to big tech.", "$45–55/hr");

        addPost("2",  "Backend Intern",        "ResMed",      "San Diego, CA",     "2026-02-08",
                "Develop high-performance backend services using Java Spring Boot for ResMed's cloud-connected healthcare devices. You will work on microservice architectures, implement secure REST APIs, and contribute to CI/CD pipelines. The team focuses on reliability and data integrity for medical-grade software. You'll gain exposure to HIPAA-compliant systems, distributed messaging queues, and real-time data processing in a meaningful healthcare technology setting.",
                List.of("Java", "Spring Boot", "REST APIs"), "#",
                new CompanyInfo("8,000+ employees", "1989", "Digital health & medical devices"),
                "★★★☆☆  Moderate match — Strong Java background needed.",
                "Medium-Low — Large company with multiple intern openings.", "$40–50/hr");

        addPost("3",  "Frontend Intern",       "Stripe",      "Seattle, WA",       "2026-02-08",
                "Craft beautiful and performant UI components for the Stripe dashboard, used by millions of businesses worldwide. You will work with TypeScript and React to build accessible, pixel-perfect interfaces that handle complex financial data visualizations. Collaborate closely with designers and product managers to ship features that improve the developer experience. You'll also contribute to Stripe's open-source design system and internal tooling infrastructure.",
                List.of("TypeScript", "React", "CSS"), "#",
                new CompanyInfo("8,000+ employees", "2010", "Online payment processing & fintech infrastructure"),
                "★★★★★  Excellent match — TypeScript + React are your core strengths.",
                "High — Very competitive; strong portfolio helps.", "$55–65/hr");

        addPost("4",  "ML Engineer Intern",    "OpenAI",      "San Francisco, CA", "2026-02-07",
                "Research and implement machine-learning models at scale within OpenAI's applied AI team. You will experiment with large language models, design evaluation benchmarks, and optimize training pipelines using distributed GPU clusters. The role requires strong fundamentals in deep learning, proficiency in Python and PyTorch, and an eagerness to push the boundaries of AI capabilities. This is a unique opportunity to work alongside world-class researchers on cutting-edge AI systems.",
                List.of("Python", "PyTorch", "ML fundamentals"), "#",
                new CompanyInfo("1,500+ employees", "2015", "Artificial intelligence research & deployment"),
                "★★★☆☆  Moderate match — Requires deep ML specialization.",
                "Very High — Extremely selective; research experience preferred.", "$65–80/hr");

        addPost("5",  "Data Engineer Intern",  "Snowflake",   "Bellevue, WA",      "2026-02-07",
                "Design and optimize large-scale data pipelines on Snowflake's cloud-native data platform. You will build ETL workflows using Python and Spark, write complex SQL queries for data transformation, and help maintain the reliability of petabyte-scale data warehouses. Work with cross-functional teams to ensure data quality and accessibility for downstream analytics and machine learning workloads. Gain hands-on experience with modern cloud data architecture and best practices.",
                List.of("SQL", "Python", "Spark"), "#",
                new CompanyInfo("5,000+ employees", "2012", "Cloud data platform & analytics"),
                "★★★★☆  Strong match — Solid SQL and Python skills.",
                "Medium — Growing team with steady intern demand.", "$50–60/hr");

        addPost("6",  "iOS Intern",            "Apple",       "Cupertino, CA",     "2026-02-06",
                "Build next-generation iOS features using Swift and SwiftUI on Apple's flagship products. Collaborate with world-class designers and engineers to prototype, develop, and ship user-facing features to billions of devices. You'll dive deep into performance optimization, accessibility standards, and Apple's Human Interface Guidelines. The team values craftsmanship, attention to detail, and a passion for creating delightful user experiences that define the future of mobile computing.",
                List.of("Swift", "SwiftUI", "Xcode"), "#",
                new CompanyInfo("160,000+ employees", "1976", "Consumer electronics, software & services"),
                "★★☆☆☆  Low match — Requires iOS/Swift specialization.",
                "High — Extremely competitive; Apple internships are highly sought after.", "$55–70/hr");

        addPost("7",  "Cloud Intern",          "AWS",         "Seattle, WA",       "2026-02-05",
                "Work on AWS core cloud infrastructure services that power millions of customers globally. You will design and implement features for distributed systems, contribute to service reliability and scalability, and participate in operational excellence initiatives. The role offers exposure to large-scale system design, networking fundamentals, and Linux internals. Collaborate with experienced engineers who build the backbone of the modern internet and cloud computing ecosystem.",
                List.of("AWS", "Linux", "Distributed Systems"), "#",
                new CompanyInfo("1,500,000+ employees (Amazon)", "2006", "Cloud computing infrastructure & services"),
                "★★★☆☆  Moderate match — Systems knowledge beneficial.",
                "Medium-High — Large hiring volume but high bar.", "$50–65/hr");

        addPost("8",  "Security Intern",       "CrowdStrike", "Austin, TX",        "2026-02-05",
                "Analyze real-world cyber threats and build advanced detection tools for CrowdStrike's endpoint security platform. You will study malware behaviors, develop signature-based and behavioral detection rules, and contribute to threat intelligence feeds. The role demands strong C/C++ skills, understanding of operating system internals, and networking protocols. Join a team of elite security researchers protecting enterprises from the world's most sophisticated cyber adversaries.",
                List.of("C/C++", "Networking", "Security"), "#",
                new CompanyInfo("7,000+ employees", "2011", "Cybersecurity & endpoint protection"),
                "★★☆☆☆  Low match — Specialized security domain.",
                "Medium — Niche field with fewer applicants.", "$45–55/hr");

        addPost("9",  "DevOps Intern",         "HashiCorp",   "Remote",            "2026-02-04",
                "Improve CI/CD pipelines and infrastructure-as-code tooling at HashiCorp, the company behind Terraform, Vault, and Consul. You will automate deployment workflows, optimize build systems, and contribute to open-source projects used by thousands of organizations. Gain experience with containerization, cloud orchestration, and modern DevOps practices. This remote-first role offers flexibility while working with a distributed engineering team passionate about developer productivity.",
                List.of("Terraform", "Docker", "CI/CD"), "#",
                new CompanyInfo("2,000+ employees", "2012", "Infrastructure automation & DevOps tooling"),
                "★★★☆☆  Moderate match — DevOps experience would strengthen fit.",
                "Medium-Low — Remote role attracts broad pool but hiring is steady.", "$45–55/hr");

        addPost("10", "Embedded Intern",       "NVIDIA",      "Santa Clara, CA",   "2026-02-04",
                "Develop low-level firmware and driver software for NVIDIA's next-generation GPU architectures. You will write performance-critical code in C/C++ and CUDA, debug hardware-software interactions, and optimize compute kernels for AI and graphics workloads. Collaborate with silicon design teams to bring cutting-edge GPU features from tape-out to production. This role is ideal for engineers passionate about high-performance computing and pushing the limits of parallel processing.",
                List.of("C/C++", "CUDA", "Embedded Systems"), "#",
                new CompanyInfo("26,000+ employees", "1993", "GPU & AI computing hardware"),
                "★★☆☆☆  Low match — Requires embedded/CUDA expertise.",
                "High — Specialized role; strong C/C++ required.", "$50–65/hr");
    }

    private void addPost(String id, String title, String company, String base, String date,
                         String description, List<String> requirements, String applyLink,
                         CompanyInfo companyInfo, String fitScore, String difficulty, String avgSalary) {
        internPosts.put(id, new InternPost(id, title, company, base, date, description,
                requirements, applyLink, companyInfo, fitScore, difficulty, avgSalary));
    }

    public List<InternPost> getAllPosts() {
        return new ArrayList<>(internPosts.values());
    }

    public Optional<InternPost> getPostById(String id) {
        return Optional.ofNullable(internPosts.get(id));
    }
}
