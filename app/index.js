const express = require("express");
const userRoutes = require("./modules/user/user.routes");

const app = express();
const PORT = process.env.PORT || 3000;

app.use(express.json());

app.get("/", (_req, res) => {
  res.json({
    message: "User API is running",
    endpoints: {
      addUser: "POST /users",
      fetchUsers: "GET /users",
      fetchUserById: "GET /users/:id",
      deleteUser: "DELETE /users/:id",
    },
  });
});

app.use("/users", userRoutes);

app.listen(PORT, () => {
  console.log(`Server listening on http://localhost:${PORT}`);
});
