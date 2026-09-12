const express = require("express");
const houseController = require("./house.controller");

const router = express.Router();

router.post("/", houseController.addHouse);
router.get("/", houseController.fetchHouses);
router.get("/:id", houseController.fetchHouseById);
router.delete("/:id", houseController.deleteHouse);

module.exports = router;
