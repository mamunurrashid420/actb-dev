describe("Smoke", () => {
  it("loads the login page", () => {
    cy.visit("/auth/login");
    cy.contains("Login to your account").should("exist");
  });
});
