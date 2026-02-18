<div className={styles["page"]}>
  {/* 页面头部 */}
  <header className={styles["header"]}>
    <div className={styles["logo"]} />
    <nav className={styles["nav"]}>
      <a className={styles["nav-item"]}>首页</a>
      <a className={styles["nav-item"]}>产品</a>
      <a className={styles["nav-item"]}>关于</a>
      <a className={styles["nav-item"]}>联系</a>
    </nav>
    <div className={styles["user-actions"]}>
      <button className={styles["btn-login"]}>登录</button>
      <button className={styles["btn-register"]}>注册</button>
    </div>
  </header>
  
  {/* 主体内容 */}
  <main className={styles["main-content"]}>
    <div className={styles["sidebar"]}>
      <div className={styles["sidebar-header"]}>
        <h3 className={styles["sidebar-title"]}>菜单</h3>
      </div>
      <ul className={styles["menu-list"]}>
        <li className={styles["menu-item"]}>选项一</li>
        <li className={styles["menu-item"]}>选项二</li>
        <li className={styles["menu-item"]}>选项三</li>
        <li className={styles["menu-item"]}>选项四</li>
      </ul>
    </div>
    
    <div className={styles["content-area"]}>
      <div className={styles["content-header"]}>
        <h1 className={styles["page-title"]}>页面标题</h1>
        <div className={styles["breadcrumb"]}>
          <span className={styles["breadcrumb-item"]}>首页</span>
          <span className={styles["breadcrumb-separator"]}>/</span>
          <span className={styles["breadcrumb-item"]}>当前页</span>
        </div>
      </div>
      
      <div className={styles["card-grid"]}>
        <div className={styles["card"]}>
          <div className={styles["card-icon"]} />
          <h4 className={styles["card-heading"]}>卡片一</h4>
          <p className={styles["card-description"]}>描述文字</p>
        </div>
        <div className={styles["card"]}>
          <div className={styles["card-icon"]} />
          <h4 className={styles["card-heading"]}>卡片二</h4>
          <p className={styles["card-description"]}>描述文字</p>
        </div>
        <div className={styles["card"]}>
          <div className={styles["card-icon"]} />
          <h4 className={styles["card-heading"]}>卡片三</h4>
          <p className={styles["card-description"]}>描述文字</p>
        </div>
      </div>
      
      <div className={styles["data-table"]}>
        <table className={styles["table"]}>
          <thead className={styles["table-header"]}>
            <tr className={styles["table-row"]}>
              <th className={styles["table-cell"]}>列一</th>
              <th className={styles["table-cell"]}>列二</th>
              <th className={styles["table-cell"]}>列三</th>
            </tr>
          </thead>
          <tbody className={styles["table-body"]}>
            <tr className={styles["table-row"]}>
              <td className={styles["table-cell"]}>数据1</td>
              <td className={styles["table-cell"]}>数据2</td>
              <td className={styles["table-cell"]}>数据3</td>
            </tr>
            <tr className={styles["table-row"]}>
              <td className={styles["table-cell"]}>数据4</td>
              <td className={styles["table-cell"]}>数据5</td>
              <td className={styles["table-cell"]}>数据6</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </main>
  
  {/* 页面底部 */}
  <footer className={styles["footer"]}>
    <div className={styles["footer-content"]}>
      <div className={styles["footer-section"]}>
        <h5 className={styles["footer-heading"]}>关于我们</h5>
        <p className={styles["footer-text"]}>公司简介</p>
      </div>
      <div className={styles["footer-section"]}>
        <h5 className={styles["footer-heading"]}>联系方式</h5>
        <p className={styles["footer-text"]}>联系信息</p>
      </div>
      <div className={styles["footer-section"]}>
        <h5 className={styles["footer-heading"]}>友情链接</h5>
        <p className={styles["footer-text"]}>链接列表</p>
      </div>
    </div>
    <div className={styles["copyright"]}>
      <span className={styles["copyright-text"]}>© 2026 版权所有</span>
    </div>
  </footer>
</div>
