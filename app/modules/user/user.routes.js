const express = require("express");
const userController = require("./user.controller");

const router = express.Router();

router.post("/", userController.addUser);
router.get("/", userController.fetchUsers);
router.get("/:id", userController.fetchUserById);
router.delete("/:id", userController.deleteUser);

module.exports = router;
