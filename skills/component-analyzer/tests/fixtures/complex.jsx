/**
 * 复杂组件 - Complex
 * 
 * 测试用例：复杂组件，包含 30+ 个 JSX 元素
 * 用途：测试复杂组件的解析、分析和性能
 */

import React, { useState, useEffect } from 'react';
import styles from './index.module.css';

const Complex = ({ 
  data = [],
  title = '',
  subtitle = '',
  onItemClick,
  onLoadMore,
  loading = false,
  error = null
}) => {
  const [activeIndex, setActiveIndex] = useState(0);
  const [isExpanded, setIsExpanded] = useState(false);

  useEffect(() => {
    // 模拟数据加载
    console.log('Component mounted');
  }, []);

  return (
    <div className={styles["wrapper"]}>
      <section className={styles["hero-section"]}>
        <div className={styles["hero-content"]}>
          <h1 className={styles["main-title"]}>{title}</h1>
          <h2 className={styles["sub-title"]}>{subtitle}</h2>
          <p className={styles["hero-description"]}>
            这是一个复杂的测试组件，包含多个嵌套层级和丰富的 JSX 结构。
          </p>
          <div className={styles["hero-actions"]}>
            <button className={styles["btn-primary"]}>主要操作</button>
            <button className={styles["btn-secondary"]}>次要操作</button>
          </div>
        </div>
        <div className={styles["hero-image"]}>
          <img className={styles["image"]} src="/hero.jpg" alt="Hero" />
        </div>
      </section>

      <section className={styles["features-section"]}>
        <div className={styles["features-grid"]}>
          <div className={styles["feature-card"]}>
            <div className={styles["feature-icon"]}>🚀</div>
            <h3 className={styles["feature-title"]}>快速</h3>
            <p className={styles["feature-desc"]}>高性能渲染</p>
          </div>
          <div className={styles["feature-card"]}>
            <div className={styles["feature-icon"]}>🎨</div>
            <h3 className={styles["feature-title"]}>美观</h3>
            <p className={styles["feature-desc"]}>精美界面设计</p>
          </div>
          <div className={styles["feature-card"]}>
            <div className={styles["feature-icon"]}>🔒</div>
            <h3 className={styles["feature-title"]}>安全</h3>
            <p className={styles["feature-desc"]}>企业级安全</p>
          </div>
          <div className={styles["feature-card"]}>
            <div className={styles["feature-icon"]}>⚡</div>
            <h3 className={styles["feature-title"]}>高效</h3>
            <p className={styles["feature-desc"]}>优化性能</p>
          </div>
        </div>
      </section>

      <section className={styles["content-section"]}>
        <div className={styles["content-header"]}>
          <h2 className={styles["section-title"]}>内容列表</h2>
          <div className={styles["section-controls"]}>
            <button className={styles["control-btn"]}>筛选</button>
            <button className={styles["control-btn"]}>排序</button>
          </div>
        </div>
        
        {loading && (
          <div className={styles["loading-state"]}>
            <div className={styles["spinner"]} />
            <span className={styles["loading-text"]}>加载中...</span>
          </div>
        )}
        
        {error && (
          <div className={styles["error-state"]}>
            <div className={styles["error-icon"]}>⚠️</div>
            <p className={styles["error-message"]}>{error}</p>
            <button className={styles["retry-btn"]}>重试</button>
          </div>
        )}
        
        <div className={styles["list-container"]}>
          {data.map((item, index) => (
            <div 
              key={item.id} 
              className={styles["list-item"]}
              onClick={() => onItemClick && onItemClick(item)}
            >
              <div className={styles["item-avatar"]}>
                <img className={styles["avatar-img"]} src={item.avatar} alt={item.name} />
              </div>
              <div className={styles["item-content"]}>
                <h4 className={styles["item-title"]}>{item.title}</h4>
                <p className={styles["item-description"]}>{item.description}</p>
                <div className={styles["item-meta"]}>
                  <span className={styles["meta-tag"]}>{item.category}</span>
                  <span className={styles["meta-date"]}>{item.date}</span>
                </div>
              </div>
              <div className={styles["item-actions"]}>
                <button className={styles["action-btn"]}>编辑</button>
                <button className={styles["action-btn"]}>删除</button>
              </div>
            </div>
          ))}
        </div>
        
        <div className={styles["load-more"]}>
          <button className={styles["load-more-btn"]} onClick={onLoadMore}>
            加载更多
          </button>
        </div>
      </section>

      <section className={styles["stats-section"]}>
        <div className={styles["stats-grid"]}>
          <div className={styles["stat-item"]}>
            <div className={styles["stat-value"]}>1,234</div>
            <div className={styles["stat-label"]}>用户</div>
          </div>
          <div className={styles["stat-item"]}>
            <div className={styles["stat-value"]}>567</div>
            <div className={styles["stat-label"]}>订单</div>
          </div>
          <div className={styles["stat-item"]}>
            <div className={styles["stat-value"]}>89%</div>
            <div className={styles["stat-label"]}>满意度</div>
          </div>
          <div className={styles["stat-item"]}>
            <div className={styles["stat-value"]}>4.8</div>
            <div className={styles["stat-label"]}>评分</div>
          </div>
        </div>
      </section>

      <footer className={styles["main-footer"]}>
        <div className={styles["footer-content"]}>
          <div className={styles["footer-brand"]}>
            <div className={styles["footer-logo"]}>Logo</div>
            <p className={styles["footer-desc"]}>构建更好的 Web 应用</p>
          </div>
          <div className={styles["footer-links"]}>
            <div className={styles["link-group"]}>
              <h4 className={styles["link-title"]}>产品</h4>
              <a className={styles["link"]}>功能</a>
              <a className={styles["link"]}>定价</a>
              <a className={styles["link"]}>案例</a>
            </div>
            <div className={styles["link-group"]}>
              <h4 className={styles["link-title"]}>支持</h4>
              <a className={styles["link"]}>文档</a>
              <a className={styles["link"]}>API</a>
              <a className={styles["link"]}>社区</a>
            </div>
            <div className={styles["link-group"]}>
              <h4 className={styles["link-title"]}>公司</h4>
              <a className={styles["link"]}>关于</a>
              <a className={styles["link"]}>博客</a>
              <a className={styles["link"]}>招聘</a>
            </div>
          </div>
        </div>
        <div className={styles["footer-bottom"]}>
          <p className={styles["copyright"]}>© 2024 Company. All rights reserved.</p>
          <div className={styles["social-links"]}>
            <a className={styles["social-link"]}>Twitter</a>
            <a className={styles["social-link"]}>GitHub</a>
            <a className={styles["social-link"]}>LinkedIn</a>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Complex;
